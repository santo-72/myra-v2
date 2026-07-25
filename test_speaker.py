import pyaudio
import numpy as np
import time

p = pyaudio.PyAudio()
stream = p.open(format=pyaudio.paFloat32,
                channels=1,
                rate=44100,
                output=True)

volume = 0.5     # range [0.0, 1.0]
fs = 44100       # sampling rate, Hz, must be integer
duration = 2.0   # in seconds, may be float
f = 440.0        # sine frequency, Hz, may be float

print("Playing sine wave...")
samples = (np.sin(2*np.pi*np.arange(fs*duration)*f/fs)).astype(np.float32)
stream.write(volume*samples)

stream.stop_stream()
stream.close()
p.terminate()
print("Done")
