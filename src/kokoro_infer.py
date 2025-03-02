# kokoro_infer.py
#
# Nath UI Project
# DOF Studio/Nathmath all rights reserved
# Open sourced under Apache 2.0 License

# Backend #####################################################################

# des
#
# This is a file that calls kokoro-82M TTS model to 
# generate voice from text.
# External library may be needed.

# Install kokoro
# !pip install -q kokoro>=0.3.4 soundfile
# !pip install misaki[ja] misaki[zh]
# !apt-get -qq -y install espeak-ng > /dev/null 2>&1


import os
import threading
import time
import numpy as np
import sounddevice as sd # pip install sounddevice
import soundfile as sf
from kokoro import KPipeline
from IPython.display import display, Audio
from typing import List, Any

from debug import nathui_global_debug
from threadpool import ThreadPool


# kokoro_language_dict
kokoro_language_dict = {
    "English": "a", # American English
    "British": "b", # British English
    "Chinese": "z",
    "Spanish": "e",
    "French": "f",
    "Hindi": "h",
    "Italian": "i",
    "Portuguese": "p"
    }

# kokoro_voicer_dict
kokoro_voicer_dict = {
    "a": [
        "af_heart", "af_alloy", "af_aoede", "af_bella", "af_jessica", "af_kore",
        "af_nicole", "af_nova", "af_river", "af_sarah", "af_sky", "am_adam",
        "am_echo", "am_eric", "am_fenrir", "am_liam", "am_michael", "am_onyx",
        "am_puck", "am_santa"
    ],
    "b": [
        "bf_alice", "bf_emma", "bf_isabella", "bf_lily", "bm_daniel", "bm_fable",
        "bm_george", "bm_lewis"
    ],
    "j": [
        "jf_alpha", "jf_gongitsune", "jf_nezumi", "jf_tebukuro", "jm_kumo"
    ],
    "z": [
        "zf_xiaobei", "zf_xiaoni", "zf_xiaoxiao", "zf_xiaoyi", "zm_yunjian",
        "zm_yunxi", "zm_yunxia", "zm_yunyang"
    ],
    "e": [
        "ef_dora", "em_alex", "em_santa"
    ],
    "f": [
        "ff_siwis"
    ],
    "h": [
        "hf_alpha", "hf_beta", "hm_omega", "hm_psi"
    ],
    "i": [
        "if_sara", "im_nicola"
    ],
    "p": [
        "pf_dora", "pm_alex", "pm_santa"
    ]
}

# Audio Player (Async)
class AudioPlayer:
    """
    This class monitors an audio list and plays new audio segments automatically.
    When a new segment is appended to the list, the monitor detects it and plays it.
    The playback counter can be reset manually, and the playback can be stopped.
    """
    def __init__(self, audio_list, sample_rate=24000, bit_rate = 16):
        """
        Initialize the RealtimeAudioPlayer.
        
        Parameters:
            audio_list (list): A reference to the list where audio segments (numpy arrays) are appended.
            sample_rate (int): The sample rate of the audio data.
        """
        self.audio_list = audio_list
        self.sample_rate = sample_rate
        self.bit_rate = bit_rate
        self.current_index = 0    # Keeps track of the next segment to play.
        self.max_index = 100**10  # A large number
        self._stop_event = threading.Event()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)


    def rebind(self, audio_list):
        """
        Rebind the audio_list.
        """
        self.audio_list = audio_list

    def start(self):
        """
        Start monitoring the audio list for new segments.
        """
        if not self._thread.is_alive():
            self._stop_event.clear()
            self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
            self._thread.start()
            
    def finale(self):
        """
        Set that no audio will be appended later.
        """
        self.max_index = len(self.audio_list)

    def stop(self):
        """
        Stop monitoring and playing audio.
        """
        self._stop_event.set()
        self.current_index = 0                    
        self.max_index = 100**10
        
    def wait_until_stop(self):
        """
        Block until the monitoring thread has completely terminated.
        """
        self._thread.join()
        self.current_index = 0
        self.max_index = 100**10

    def reset_counter(self, index=0):
        """
        Reset the playback counter.
        
        Parameters:
            index (int): The new counter value (default is 0).
        """
        self.current_index = index

    def _monitor_loop(self):
        """Internal loop that checks for new audio segments and plays them using a blocking OutputStream."""
        while not self._stop_event.is_set():
            if self.current_index < len(self.audio_list):
                audio = self.audio_list[self.current_index]
                audio = np.array(audio)
                self.current_index += 1

                # Convert audio to float32 and normalize if necessary.
                if audio.dtype != np.float32:
                    audio = audio.astype(np.float32)
                max_val = np.max(np.abs(audio))
                if max_val > 1:
                    audio = audio / max_val

                # Determine the number of channels.
                channels = 1 if audio.ndim == 1 else audio.shape[1]

                # Use a blocking OutputStream to ensure playback finishes before returning.
                with sd.OutputStream(samplerate=self.sample_rate, channels=channels, dtype='float32') as stream:
                    if nathui_global_debug == True:
                        print("playing ... ", audio)
                    stream.write(audio)
            else:
                if self.current_index >= self.max_index:
                    self.current_index = 0
                    self.max_index = 100**10
                    break
                time.sleep(0.05)

# Kokoro Generator
class KokoroTTS:
    """
    A product-level, realtime TTS class using the KPipeline engine.
    This class supports highly adjustable parameters such as language, voice, speed,
    split pattern, sample rate, display, and file saving options.
    """
    def __init__(self, lang_code='z', voice='zf_xiaoni', speed=1, split_pattern=r'\n+', 
                 sample_rate=24000, display_audio=True, save_to_file=False, output_dir='./__kokoro_audio__'):
        """
        Initialize the realtime TTS engine.
        
        Parameters:
            lang_code (str): Language code (e.g., 'z' for Mandarin Chinese).
            voice (str): The voice preset to use (e.g., 'zf_xiaoni').
            speed (float): Speaking speed multiplier.
            split_pattern (str): Regex pattern to split input text into segments.
            sample_rate (int): Audio sample rate.
            display_audio (bool): Whether to display audio playback (for notebook environments).
            save_to_file (bool): Whether to save each generated audio segment as a WAV file.
            output_dir (str): Directory where audio files will be saved.
        """
        self.lang_code = lang_code
        self.voice = voice
        self.speed = speed
        self.split_pattern = split_pattern
        self.sample_rate = sample_rate
        self.display_audio = display_audio
        self.save_to_file = save_to_file
        self.output_dir = output_dir
        
        # Create output directory if file saving is enabled
        if self.save_to_file and not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
            
        # Initialize the TTS pipeline with the given language code
        self.pipeline = KPipeline(lang_code=self.lang_code)
        
    # Update any parameter here
    def update_parameters(self, **kwargs):
        """
        Update parameters dynamically. Valid keys include:
        'lang_code', 'voice', 'speed', 'split_pattern', 'sample_rate', 
        'display_audio', 'save_to_file', and 'output_dir'.
        """
        for key, value in kwargs.items():
            if hasattr(self, key):
                setattr(self, key, value)
                # If language code is updated, reinitialize the pipeline.
                if key == 'lang_code':
                    self.pipeline = KPipeline(lang_code=value)
            else:
                raise ValueError(f"Invalid parameter: {key}")
        # Ensure output directory exists when saving is enabled.
        if self.save_to_file and not os.path.exists(self.output_dir):
            os.makedirs(self.output_dir)
        
    # Generate audio in realtime and yields
    def synthesize(self, text):
        """
        Synthesize the provided text into audio segments in realtime.
        Each segment is generated based on the split pattern.
        
        Parameters:
            text (str): The full text to be synthesized.
            
        Yields:
            tuple: (graphemes, phonemes, audio data)
        """
        taskid = str(hash(text))
        if os.path.exists(self.output_dir) == False:
            os.makedirs(self.output_dir)
        
        generator = self.pipeline(
            text, 
            voice=self.voice,
            speed=self.speed, 
            split_pattern=self.split_pattern
        )
        
        for idx, (graphemes, phonemes, audio) in enumerate(generator):
            # Display audio if enabled (works in Jupyter environments)
            if self.display_audio:
                display(Audio(data=audio, rate=self.sample_rate, autoplay=(idx==0)))
            # Save audio file if enabled
            if self.save_to_file:
                filename = os.path.join(self.output_dir, f'task_{taskid}_segment_{idx}.wav')
                sf.write(filename, audio, self.sample_rate)
            yield graphemes, phonemes, audio
          
    # Generate audio and accumulate and then return all
    def synthesize_accumulate(self, text) -> List[Any]:
        """
        Synthesize the provided text into audio segments and accumulate them
        
        Parameters:
            text (str): The full text to be synthesized.
            
        Return
            list[ tuple: (graphemes, phonemes, audio data)]
        """
        accumulated = []
        for segment_index, (graphemes, phonemes, audio) in enumerate(self.synthesize(text)):
            tup = (graphemes, phonemes, audio)
            accumulated.append(tup)
            
        return accumulated
            
    
# Try generate - test (threading)
def try_generate(player, audios):
    sample_text = '''
    人民，只有人民，才是创造世界历史的动力。
    战略上要藐视敌人，战术上要重视敌人。
    与天奋斗，其乐无穷！与地奋斗，其乐无穷！与人奋斗，其乐无穷！
    '''
    
    # Create and start the realtime audio player.
    player.start()
    

    # Generate audio
    tts_engine = KokoroTTS(lang_code='z', voice='zf_xiaoni', speed=1, 
                             split_pattern=r'(?:\n+|[.。；;!！]+)', sample_rate=24000, 
                             display_audio=True, save_to_file=True, output_dir='kokoro_audio')
    
    # Generate and process audio segments in realtime.
    for segment_index, (graphemes, phonemes, audio) in enumerate(tts_engine.synthesize(sample_text)):
        audios.append(audio)
        print(f"Segment {segment_index}")
        print("Text:", graphemes)
        print("Phonemes:", phonemes)
        
    # Finale
    player.finale()
        
    # Wait until stop
    player.wait_until_stop()
        
    return player

# Example usage and test case
if __name__ == '__main__':

    audios = []
    player = AudioPlayer(audios, sample_rate=24000)
    
    tp = ThreadPool(4)
    task_id = tp.execute(try_generate, player = player, audios = audios)
    
    player.stop()
    tp.stopall()
    tp.shutdown()