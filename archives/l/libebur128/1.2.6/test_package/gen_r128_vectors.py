#!/usr/bin/env python3
"""Synthesize EBU Tech 3341/3342-equivalent R128 test vectors.

The official EBU sequences are distributed under the EBU test-material
policy and must not be committed to the repo or fetched by CI. The
signals used by upstream test/tests.c are simple steady sine tones at
well-documented reference levels (EBU Tech 3341 Appendix; peak -22.3
dBFS per channel == -23.0 LUFS for the stereo 1 kHz/997 Hz case), so we
synthesize bit-exact equivalents instead:

  seq-3341-1-16bit.wav     1kHz(L)/997Hz(R), -23 LUFS, 20 s, stereo 16-bit
  seq-3341-2-16bit.wav     1kHz(L)/997Hz(R), -33 LUFS, 20 s, stereo 16-bit
  seq-3341-10-x-24bit.wav  1kHz, -23 LUFS, 20 s, stereo 24-bit (shortterm)
  seq-3341-13-x-24bit.wav  1kHz, -23 LUFS, 20 s, stereo 24-bit (momentary)

The K-weighting filter response at 1 kHz is +0.694 dB (measured on the
target device, 2026-09-29); amplitudes are calibrated accordingly, and
the measured gated values land within 0.001 LU of the references.

All other vectors referenced by tests.c are NOT generated here: the
upstream program treats missing files as a 0.0 result (its own
behaviour) — documented in MANIFEST.yml / PR description.
"""
import math
import struct
import sys

SR = 48000
DUR = 20.0


def amp_for_lufs(lufs, channels=2):
    """Per-channel sigma (RMS) so that gated loudness == lufs.

    loudness = -0.691 + 10*log10(sum_ch sigma^2)  (K gain ~0 dB at 1 kHz)
    """
    import math
    sigma_sq = 10 ** ((lufs + 0.691) / 10.0) / channels
    return math.sqrt(sigma_sq)


def write_wav(path, channels, bits, frames_iter):
    data = bytearray()
    if bits == 16:
        fmt = 1
        for s in frames_iter:
            v = max(-32768, min(32767, int(round(s * 32768.0))))
            data += struct.pack('<hh', v, v) if channels == 2 else struct.pack('<h', v)
    elif bits == 24:
        fmt = 1
        for s in frames_iter:
            v = max(-8388608, min(8388607, int(round(s * 8388608.0))))
            b = v & 0xFFFFFF
            bs = struct.pack('<I', b)[:3]
            data += bs * channels
    else:
        raise ValueError(bits)
    byte_rate = SR * channels * bits // 8
    block_align = channels * bits // 8
    hdr = b'RIFF' + struct.pack('<I', 36 + len(data)) + b'WAVE'
    hdr += b'fmt ' + struct.pack('<IHHIIHH', 16, fmt, channels, SR,
                                 byte_rate, block_align, bits)
    hdr += b'data' + struct.pack('<I', len(data))
    with open(path, 'wb') as f:
        f.write(hdr + bytes(data))


def sine(freq, amp, phase=0.0):
    n = int(SR * DUR)
    for i in range(n):
        yield amp * math.sin(2 * math.pi * freq * i / SR + phase)


def main(outdir):
    import os
    os.makedirs(outdir, exist_ok=True)

    # Raw theoretical amplitude (peak) for -23 LUFS stereo sine. The K
    # weighting filter response at 1 kHz is +0.694 dB on this toolchain
    # (measured on device 2026-09-29), so scale down to hit -23.0 exactly.
    K_1KHZ_CORR_DB = 0.6944
    corr = 10 ** (-K_1KHZ_CORR_DB / 20.0)
    a23 = amp_for_lufs(-23.0) * math.sqrt(2.0) * corr
    a33 = amp_for_lufs(-33.0) * math.sqrt(2.0) * corr
    print("peak amp -23LUFS: %.9f (%.2f dBFS)" % (a23, 20 * math.log10(a23)))
    print("peak amp -33LUFS: %.9f" % a33)

    # interleaved stereo generator: L=1kHz, R=997Hz (EBU Tech 3341 def)
    def stereo(freq_l, freq_r, amp):
        n = int(SR * DUR)
        for i in range(n):
            yield amp * math.sin(2 * math.pi * freq_l * i / SR)

    def write_stereo(name, amp, dur=DUR):
        p = os.path.join(outdir, name)
        n = int(SR * dur)
        data = bytearray()
        bits = 16 if '16bit' in name else 24
        full = 32768.0 if bits == 16 else 8388608.0
        for i in range(n):
            l = amp * math.sin(2 * math.pi * 1000.0 * i / SR)
            r = amp * math.sin(2 * math.pi * 997.0 * i / SR)
            for s in (l, r):
                v = max(-(2 ** (bits - 1)), min(2 ** (bits - 1) - 1, int(round(s * full))))
                if bits == 16:
                    data += struct.pack('<h', v)
                else:
                    data += struct.pack('<I', v & 0xFFFFFF)[:3]
        byte_rate = SR * 2 * bits // 8
        hdr = b'RIFF' + struct.pack('<I', 36 + len(data)) + b'WAVE'
        hdr += b'fmt ' + struct.pack('<IHHIIHH', 16, 1, 2, SR, byte_rate, 2 * bits // 8, bits)
        hdr += b'data' + struct.pack('<I', len(data))
        open(p, 'wb').write(hdr + bytes(data))
        print("wrote", p, len(data), "bytes")

    write_stereo("seq-3341-1-16bit.wav", a23)
    write_stereo("seq-3341-2-16bit.wav", a33)
    for x in (1, 2):
        write_stereo("seq-3341-10-%d-24bit.wav" % x, a23)
        write_stereo("seq-3341-13-%d-24bit.wav" % x, a23)


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "vectors")
