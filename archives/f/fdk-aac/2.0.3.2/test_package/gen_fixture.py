#!/usr/bin/env python3
"""生成确定性测试 WAV(441Hz 纯正弦表, 2s@44.1kHz mono)。

无官方 Xiph fixture 时,phase 3 用它烟测官方工具 test-encode-decode
(退出码 + 哈希行形状);官方 fixture 套件的位元比对不受此文件影响。
正弦表为编译期常量(与 probe.c 同一张表),与 math.sin 实现无关,同架构
跨平台位元可复现。纯正弦保证官方工具全模式矩阵(含无 afterburner 的
AAC-LC)解码平均误差落在上游 avg_diff 阈值内;probe.c 自身用正弦表
+LCG 噪声的更严合成。

用法: python3 gen_fixture.py <out.wav>
"""
import struct
import sys
import wave

RATE = 44100
SECS = 2

# 441Hz 正弦表:44100/441 = 100 样本/周期,幅值 16000(与 probe.c 同表)
SINE_TAB = [
    0, 1005, 2005, 2998, 3979, 4944, 5890, 6812, 7708, 8573,
    9405, 10199, 10953, 11663, 12328, 12944, 13509, 14021, 14477, 14876,
    15217, 15497, 15717, 15874, 15968, 16000, 15968, 15874, 15717, 15497,
    15217, 14876, 14477, 14021, 13509, 12944, 12328, 11663, 10953, 10199,
    9405, 8573, 7708, 6812, 5890, 4944, 3979, 2998, 2005, 1005,
    0, -1005, -2005, -2998, -3979, -4944, -5890, -6812, -7708, -8573,
    -9405, -10199, -10953, -11663, -12328, -12944, -13509, -14021, -14477, -14876,
    -15217, -15497, -15717, -15874, -15968, -16000, -15968, -15874, -15717, -15497,
    -15217, -14876, -14477, -14021, -13509, -12944, -12328, -11663, -10953, -10199,
    -9405, -8573, -7708, -6812, -5890, -4944, -3979, -2998, -2005, -1005,
]


def gen(path):
    n = RATE * SECS
    frames = bytearray()
    for i in range(n):
        frames += struct.pack("<h", SINE_TAB[i % 100])
    with wave.open(path, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(RATE)
        w.writeframes(bytes(frames))


if __name__ == "__main__":
    gen(sys.argv[1] if len(sys.argv) > 1 else "probe-input.wav")
