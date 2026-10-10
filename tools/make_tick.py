"""Makes assets/snd/tick.ogg, the soft click the menus make when the highlight moves.

Needs numpy and soundfile, which the game itself does not:
    venv/bin/pip install numpy soundfile
    venv/bin/python tools/make_tick.py
"""
import numpy as np
import soundfile as sf

RATE = 22050
t = np.arange(int(RATE * 0.06)) / RATE
tone = np.sin(2 * np.pi * 1150 * t) + 0.3 * np.sin(2 * np.pi * 2300 * t)        # a small wooden knock
shape = np.minimum(t / 0.002, 1) * np.exp(-t / 0.011)                           # 2 ms in, then dies away quickly
wave = 0.32 * tone * shape / np.abs(tone * shape).max()
wave = np.concatenate([wave, np.zeros(int(RATE * 0.03))])                       # a little silence so the tail is not cut
sf.write("assets/snd/tick.ogg", wave.astype(np.float32), RATE, format="OGG", subtype="VORBIS")
print("wrote assets/snd/tick.ogg,", len(wave) / RATE, "seconds")
