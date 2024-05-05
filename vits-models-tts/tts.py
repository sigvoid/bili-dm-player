# coding=utf-8
import sys
import os
run_dir = os.path.dirname(os.path.realpath(__file__))
sys.path.append(run_dir)
import re
import argparse
import utils
import commons
import json
import torch
from models import SynthesizerTrn
from text import text_to_sequence, _clean_text
from torch import no_grad, LongTensor
import logging
logging.getLogger('numba').setLevel(logging.WARNING)
limitation = os.getenv("SYSTEM") == "spaces"  # limit text and audio length in huggingface spaces

import scipy

hps_ms = utils.get_hparams_from_file(f'{run_dir}/config/config.json')

device = torch.device('cuda') if torch.cuda.is_available() else torch.device('cpu')

tts_fn = None
voice_opt = (0.6, 0.668, 1)

def get_text(text, hps, is_symbol):
    text_norm, clean_text = text_to_sequence(text, hps.symbols, [] if is_symbol else hps.data.text_cleaners)
    if hps.data.add_blank:
        text_norm = commons.intersperse(text_norm, 0)
    text_norm = LongTensor(text_norm)
    return text_norm, clean_text

def create_tts_fn(net_g_ms, speaker_id):
    def tts_fn(text, language, noise_scale, noise_scale_w, length_scale, is_symbol):
        text = text.replace('\n', ' ').replace('\r', '').replace(" ", "")
        if limitation:
            text_len = len(re.sub("\[([A-Z]{2})\]", "", text))
            max_len = 100
            if is_symbol:
                max_len *= 3
            if text_len > max_len:
                return "Error: Text is too long", None
        if not is_symbol:
            if language == 0:
                text = f"[ZH]{text}[ZH]"
            elif language == 1:
                text = f"[JA]{text}[JA]"
            else:
                text = f"{text}"
        stn_tst, clean_text = get_text(text, hps_ms, is_symbol)
        with no_grad():
            x_tst = stn_tst.unsqueeze(0).to(device)
            x_tst_lengths = LongTensor([stn_tst.size(0)]).to(device)
            sid = LongTensor([speaker_id]).to(device)
            audio = net_g_ms.infer(x_tst, x_tst_lengths, sid=sid, noise_scale=noise_scale, noise_scale_w=noise_scale_w,
                                   length_scale=length_scale)[0][0, 0].data.cpu().float().numpy()

        return "Success", (22050, audio)
    return tts_fn

def create_to_symbol_fn(hps):
    def to_symbol_fn(is_symbol_input, input_text, temp_lang):
        if temp_lang == 0:
            clean_text = f'[ZH]{input_text}[ZH]'
        elif temp_lang == 1:
            clean_text = f'[JA]{input_text}[JA]'
        else:
            clean_text = input_text
        return _clean_text(clean_text, hps.data.text_cleaners) if is_symbol_input else ''

    return to_symbol_fn

def _LoadCharacter(name):
    with open(f"{run_dir}/pretrained_models/info.json", "r", encoding="utf-8") as f:
        models_info = json.load(f)
    for i, info in models_info.items():
        sid = info['sid']
        name_en = info['name_en']
        name_zh = info['name_zh']
        title = info['title']
        cover = f"{run_dir}/pretrained_models/{i}/{info['cover']}"
        example = info['example']
        language = info['language']
        if name == 'Any' or name == name_zh or name == name_en:
            net_g_ms = SynthesizerTrn(
                len(hps_ms.symbols),
                hps_ms.data.filter_length // 2 + 1,
                hps_ms.train.segment_size // hps_ms.data.hop_length,
                n_speakers=hps_ms.data.n_speakers if info['type'] == "multi" else 0,
                **hps_ms.model)
            utils.load_checkpoint(f'{run_dir}/pretrained_models/{i}/{i}.pth', net_g_ms, None)
            _ = net_g_ms.eval().to(device)
            tts_fn = create_tts_fn(net_g_ms, sid)
            to_symbol_fn = create_to_symbol_fn(hps_ms)
            return True, tts_fn
    return False, None

def LoadCharacter(name):
    global tts_fn
    _, tts_fn = _LoadCharacter(name)

def SetVoiceOption(ns, nsw, ls):
    global voice_opt
    voice_opt = (ns, nsw, ls)

LoadCharacter("Any")

def GenerateTTS(text):
    if tts_fn != None and voice_opt != None:
        (ns, nsw, ls) = voice_opt
        symbol_input = False
        result, (sampling_rate, output) = tts_fn(text, 0,  ns, nsw, ls, symbol_input)
        if result == "Success":
            save_path = f"{run_dir}/output.wav"
            scipy.io.wavfile.write(save_path, rate=sampling_rate, data=output.T)
            return True, save_path
        else:
            print(f'TTS: {result}')
            return False, None

__all__ = ['LoadCharacter', 'SetVoiceOption', 'GenerateTTS']
