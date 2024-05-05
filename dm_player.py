from vits-models-tts import tts
import winsound
import threading
import time

def PlaySound(filename):
    winsound.PlaySound(filename, winsound.SND_FILENAME)

class DmPlayer:

    def __init__(self):
        self.running = True
        self.dm_text_list = []
        self.th = None

    def Start(self):
        if self.th == None:
            self.th = threading.Thread(target=self.Run, args=())
            self.th.start()
    
    def Add(self, text, notify = None, callback_before = None, *args):
        self.dm_text_list.append((text, notify, callback_before, args))
        print(f'queue len: {len(self.dm_text_list)}')

    def LoadCharacter(self, name):
        tts.LoadCharacter(name)

    # ns "控制感情变化程度", minimum=0.1, maximum=1.0
    # nsw "控制音素发音长度", minimum=0.1, maximum=1.0
    # ls "控制整体语速", minimum=0.1, maximum=2.0
    def SetVoiceOption(self, ns, nsw, ls):
        tts.SetVoiceOption(ns, nsw, ls)

    def Run(self):
        text = ""
        while self.running:
            try:
                (text, notify, cb_before, args) = self.dm_text_list.pop(0)
            except:
                time.sleep(1)
            else:
                if cb_before != None:
                    cb_before(*args)

                print(f'Generating TTS {text}')
                result, wav = tts.GenerateTTS(text)
                if result == True:
                    if notify != None:
                        PlaySound(f"{notify}")
                    PlaySound(wav)

    def Terminate(self):
        self.running = False
        self.th = None