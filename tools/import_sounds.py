"""Turns the team's sound effects in art-src/Muusika into the files the game plays.

Needs numpy and soundfile, which the game itself does not:
    venv/bin/pip install numpy soundfile
    venv/bin/python tools/import_sounds.py

The files arrive with silence before and after the sound, and a sound that starts a
second late is a second late in the game. Here that silence is cut off. Otherwise a
sound is left as it is, with two exceptions: the door recording holds several creaks
one after another, of which the way out plays only the last (the cupboards get the
whole file, untouched), and the answers to a thing handed over are made louder.
"""
import shutil

import numpy as np
import soundfile as sf

SOURCE, TARGET = "art-src/Muusika", "assets/snd"
QUIET = 0.004         # anything below this, of full scale 1, counts as silence
EDGE = 0.03           # seconds kept before the sound starts, and the length of the fade at each end
ANSWER = 0.8          # how loud, at its loudest, a right or wrong answer is made


def loud(wave):
    """How loud each sample is, whatever the number of channels."""
    return np.abs(wave).max(axis=1) if wave.ndim > 1 else np.abs(wave)


def takes(wave, rate, gap=0.6):
    """(start, end) in samples of each stretch of sound that has at least `gap` seconds of silence round it."""
    sounding = np.flatnonzero(loud(wave) > QUIET)
    breaks = np.flatnonzero(np.diff(sounding) > gap * rate)
    starts = np.concatenate(([sounding[0]], sounding[breaks + 1]))
    ends = np.concatenate((sounding[breaks], [sounding[-1]]))
    return list(zip(starts, ends))


def cut(wave, rate, start, end):
    """The stretch from start to end with a little room and a short fade at both ends."""
    edge = int(EDGE * rate)
    piece = wave[max(0, start - edge):end + 2 * edge].astype(np.float64)
    fade = np.linspace(0, 1, edge)
    shape = (-1, 1) if piece.ndim > 1 else (-1,)
    piece[:edge] *= fade.reshape(shape)
    piece[-edge:] *= fade[::-1].reshape(shape)
    return piece


def save(name, piece, rate):
    sf.write(f"{TARGET}/{name}", piece.astype(np.float32), rate, format="OGG", subtype="VORBIS")
    print(f"{name:14s} {len(piece) / rate:5.2f} s, peak {np.abs(piece).max():.2f}")


def main():
    for n in (1, 2, 3):          # falling through time, into a memory and back: the whole sound, without its silent lead-in
        wave, rate = sf.read(f"{SOURCE}/portal sfx{n}.ogg")
        parts = takes(wave, rate, gap=3.0)
        save(f"portal{n}.ogg", cut(wave, rate, parts[0][0], parts[-1][1]), rate)

    # the two answers to a thing handed over. They arrive very quiet, and are brought up to
    # the level of the sounds they replace so that they are still heard over the music
    for source, name in (("success sfx.ogg", "restore.ogg"), ("failure sfx 1.ogg", "wrong.ogg")):
        wave, rate = sf.read(f"{SOURCE}/{source}")
        start, end = takes(wave, rate, gap=3.0)[0]
        piece = cut(wave, rate, start, end)
        save(name, piece * (ANSWER / np.abs(piece).max()), rate)

    wave, rate = sf.read(f"{SOURCE}/door creaking.ogg")
    parts = takes(wave, rate)
    for start, end in parts:
        print(f"   a creak from {start / rate:5.2f} to {end / rate:5.2f} s")
    start, end = parts[-1]       # the last creak is the shortest and the loudest: a door opening once
    save("door.ogg", cut(wave, rate, start, end), rate)
    # the archive's cupboards get the whole recording, every creak of it, exactly as it came
    shutil.copyfile(f"{SOURCE}/door creaking.ogg", f"{TARGET}/creak.ogg")
    print(f"creak.ogg      {len(wave) / rate:5.2f} s, the file as it is")


main()
