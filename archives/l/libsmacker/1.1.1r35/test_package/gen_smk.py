#!/usr/bin/env python3
"""Synthetic .smk (Smacker Video) generator for libsmacker consumer tests.

Byte layout is derived 1:1 from upstream smacker.c `smk_open_generic()` and
smk_hufftree.c `_smk_huff16_build()` / `_smk_huff8_build()`:

  header  : "SMK" | version | w | h | frames | ms_per_frame | video_flags
            | 7 x audio_max_buffer | tree_size | 4 x unpacked_tree_size
            | 7 x audio_rate | dummy
  index   : (frames + ring) x chunk_size(u32, low2 bits = keyframe flags)
            (frames + ring) x frame_type(u8)
  trees   : tree_size bytes of Smacker Huffman bitstream (4 big trees)
  payload : (frames + ring) x chunk data

Bit order inside the bitstream is LSB-first (see smk_bitstream.c
`_smk_bs_read_1`: `(buffer[byte] & (1 << bit_num))`).

Output: a solid-colour 8x8, 1-frame, video-only clip (block type 3 =
"SOLID BLOCK"), which exercises header parsing, Huffman tree construction,
frame render and buffer hand-off.
"""
import struct
import sys

W = 8
H = 8
FRAMES = 1
MS_PER_FRAME = 40          # -> usf = 40000
COLOR = 0x20               # typedata of the SOLID BLOCK
SMK_TYPE = 3               # block type: SOLID BLOCK
SMK_BLOCKLEN = 0           # sizetable[0] == 1 -> one 4x4 group per lookup


def lsb_bits(value, n):
    """Bits of `value`, stream order = LSB first (smk_bs_read_* order)."""
    return [(value >> i) & 1 for i in range(n)]


def enc_big_tree(low, high):
    """Encode one 16-bit Smacker Huffman tree with a single leaf.

    _smk_huff16_build():  start bit | low8 tree | hi8 tree | 3 x cache |
                           recursive big tree | end bit
    _smk_huff8_build():   start bit | recursive node | end bit
    recursive node:       bit 1 = branch, bit 0 = leaf + 8-bit value
    """
    bits = [1]                                     # big tree start bit
    for byte in (low, high):                       # low8 / hi8 tree
        bits += [1, 0]                             # huff8 start + leaf node
        bits += lsb_bits(byte, 8)                  # leaf value
        bits += [0]                                # huff8 end bit
    for _ in range(3):                             # escape-code cache[3]
        bits += lsb_bits(0, 16)                    # low byte, then high byte
    bits += [0]                                    # big tree root = leaf
    # low8 / hi8 lookups below consume 0 bits (their roots are leaves)
    bits += [0]                                    # big tree end bit
    return bits


def pack_bits(bits):
    out = bytearray()
    for i in range(0, len(bits), 8):
        chunk = bits[i:i + 8]
        byte = 0
        for j, b in enumerate(chunk):
            byte |= (b & 1) << j
        out.append(byte)
    return bytes(out)


def build_smk():
    unpack = (COLOR << 8) | (SMK_BLOCKLEN << 2) | SMK_TYPE
    trees = [
        enc_big_tree(0, 0),                         # SMK_TREE_MMAP (unused)
        enc_big_tree(0, 0),                         # SMK_TREE_MCLR (unused)
        enc_big_tree(0, 0),                         # SMK_TREE_FULL (unused)
        enc_big_tree(unpack & 0xFF, unpack >> 8),   # SMK_TREE_TYPE
    ]
    hufftree = pack_bits([b for t in trees for b in t])

    # frame payload: SOLID BLOCK lookups consume no payload bits at all
    # (the tree root is a leaf), 4 zero bytes are enough for chunk_size=4.
    payload = b"\x00\x00\x00\x00"
    chunk_size_raw = len(payload) | 0x01            # low bit = keyframe flag

    out = bytearray()
    out += b"SMK"
    out += b"4"
    out += struct.pack("<I", W)
    out += struct.pack("<I", H)
    out += struct.pack("<I", FRAMES)
    out += struct.pack("<I", MS_PER_FRAME)
    out += struct.pack("<I", 0)                     # video flags: no ring/scale
    out += struct.pack("<7I", 0, 0, 0, 0, 0, 0, 0)  # audio max buffers
    out += struct.pack("<I", len(hufftree))
    out += struct.pack("<4I", 0, 0, 0, 0)           # unpacked tree sizes
    out += struct.pack("<7I", 0, 0, 0, 0, 0, 0, 0)  # audio rate/exists
    out += struct.pack("<I", 0)                     # dummy
    out += struct.pack("<I", chunk_size_raw)
    out += bytes([0])                               # frame_type: video only
    out += hufftree
    out += payload
    return bytes(out)


def main():
    path = sys.argv[1] if len(sys.argv) > 1 else "synthetic.smk"
    data = build_smk()
    with open(path, "wb") as f:
        f.write(data)
    print("wrote %s (%d bytes)" % (path, len(data)))


if __name__ == "__main__":
    main()
