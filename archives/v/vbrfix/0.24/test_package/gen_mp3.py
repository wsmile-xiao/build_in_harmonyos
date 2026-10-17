#!/usr/bin/env python3
"""gen_mp3.py — 生成 vbrfixc 功能测试用的合成 MP3 样本。

样本为手工构造的 MPEG-1 Layer III 帧序列（无需外部音频工具）：
  - 帧头 4 字节：同步字 + MPEG1 + LayerIII + 比特率索引 + 采样率 + 声道
  - 帧长 = 144000 * bitrate_kbps / sample_rate (+padding)
  - 变化比特率 → vbrfixc 判定为 VBR 并重建 Xing 头

用法: python3 gen_mp3.py <kind> <out_path>
kind ∈ vbr_noxing | vbr_xing | cbr_noxing | vbr_id3v1 | vbr_id3v2
"""
import struct
import sys

BITRATES = [0, 32, 40, 48, 56, 64, 80, 96, 112, 128, 160, 192, 224, 256, 320]
SRATES = [44100, 48000, 32000]
# MPEG1-stereo 时 'Xing' 在帧内的偏移（与 vbrfix.cpp getXHpos(1,2) = 0x24-4 对应）
XING_OFF = 0x24 - 4
FRAME_BYTES_128K = (144000 * 128) // 44100          # 417：新增 VBR 头帧长度
N_FRAMES = 24


def frame(br_idx, sr_idx=0, chan=0, fill=0x00):
    hdr = bytes([0xFF, 0xFB, (br_idx << 4) | (sr_idx << 2), (chan << 6)])
    fsize = (144000 * BITRATES[br_idx]) // SRATES[sr_idx]
    return hdr + bytes([fill]) * (fsize - 4)


def xing_frame(br_idx=9, frames=0, bytes_=0):
    hdr = bytes([0xFF, 0xFB, (br_idx << 4), 0])
    fsize = (144000 * BITRATES[br_idx]) // SRATES[0]
    body = bytearray(fsize - 4)
    off = XING_OFF
    body[off:off + 4] = b"Xing"
    body[off + 4:off + 8] = struct.pack(">I", 15)
    body[off + 8:off + 12] = struct.pack(">I", frames)
    body[off + 12:off + 16] = struct.pack(">I", bytes_)
    return hdr + bytes(body)


def vbr_stream(n=N_FRAMES):
    # 128kbps / 160kbps 交替 → 比特率变化 → vbr=true
    return b"".join(frame(9 if i % 2 == 0 else 10) for i in range(n))


def cbr_stream(n=N_FRAMES):
    return b"".join(frame(9) for _ in range(n))


def build(kind):
    if kind == "vbr_noxing":
        return vbr_stream()
    if kind == "vbr_xing":
        return xing_frame(frames=N_FRAMES - 1) + vbr_stream()
    if kind == "cbr_noxing":
        return cbr_stream()
    if kind == "vbr_id3v1":
        return vbr_stream() + b"TAG" + b"\0" * 125
    if kind == "vbr_id3v2":
        payload = b"\0" * 40
        sz = len(payload)
        hdr = (b"ID3\x03\x00\x00"
               + bytes([(sz >> 21) & 0x7F, (sz >> 14) & 0x7F,
                        (sz >> 7) & 0x7F, sz & 0x7F]))
        return hdr + payload + vbr_stream()
    raise SystemExit("unknown sample kind: " + kind)


if __name__ == "__main__":
    if len(sys.argv) != 3:
        raise SystemExit(__doc__)
    data = build(sys.argv[1])
    with open(sys.argv[2], "wb") as fh:
        fh.write(data)
    print("%s: %s (%d bytes)" % (sys.argv[1], sys.argv[2], len(data)))
