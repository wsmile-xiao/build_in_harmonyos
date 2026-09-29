# 生成 fuzz 目标语料:真实 WebP 流(有损/无损/动画/1x1)+ 损坏/随机/截断/空 + PPM。
# 本机 PIL 生成(独立 libwebp 构建,与真机编解码器互为印证)。
import os
import random

from PIL import Image

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "seeds")
os.makedirs(OUT, exist_ok=True)


def path(name):
    return os.path.join(OUT, name)


# 64x64 高频棋盘(RGB,有损两档)
img = Image.new("RGB", (64, 64))
px = img.load()
for y in range(64):
    for x in range(64):
        px[x, y] = ((x * 7 + y * 13) & 255, (x * 11 + y * 5) & 255,
                    (x * 3 + y * 17) & 255)
img.save(path("s_lossy_q75.webp"), format="WEBP", quality=75)
img.save(path("s_lossy_q100.webp"), format="WEBP", quality=100)

# 64x64 无损 RGBA(alpha 永不为 0,规避 VP8L alpha-cleanup 语义)
rgba = Image.new("RGBA", (64, 64))
px = rgba.load()
for y in range(64):
    for x in range(64):
        px[x, y] = ((x * 7 + y * 13) & 255, (x * 11 + y * 5) & 255,
                    (x * 3 + y * 17) & 255, ((x * 7 + y * 13) & 0x7F) | 0x80)
rgba.save(path("s_vp8l_lossless.webp"), format="WEBP", lossless=True)

# 48x48 动画 3 帧
frames = []
for i in range(3):
    f = Image.new("RGBA", (48, 48))
    p = f.load()
    for y in range(48):
        for x in range(48):
            p[x, y] = ((x * 7 + y * 13 + i * 40) & 255, (x * 11 + y * 5) & 255,
                       (x * 3 + y * 17) & 255, 255)
    frames.append(f)
frames[0].save(path("s_anim_3f.webp"), format="WEBP", save_all=True,
               append_images=frames[1:], duration=30, loop=0)

# 1x1
Image.new("RGB", (1, 1), (200, 100, 50)).save(path("s_tiny.webp"),
                                              format="WEBP", quality=80)

# 损坏:RIFF-WEBP 魔数在但容器损坏(阅读器可选中、解码器必须安全拒绝)
with open(path("s_corrupt.bin"), "wb") as f:
    f.write(b"RIFF\x30\x00\x00\x00WEBP" +
            bytes(random.getrandbits(8) for _ in range(64)))

# 随机字节(无 RIFF 魔数)
with open(path("s_random.bin"), "wb") as f:
    f.write(bytes(random.getrandbits(8) for _ in range(512)))

# 截断:有效文件头 24 字节
with open(path("s_lossy_q75.webp"), "rb") as f:
    full = f.read()
with open(path("s_trunc.webp"), "wb") as f:
    f.write(full[:24])

# PPM P6 8x8(供 imageio 目标 PNM 阅读器)
with open(path("s_8x8.ppm"), "wb") as f:
    f.write(b"P6\n8 8\n255\n" + bytes(
        (x * 31 + y * 7) & 255 for y in range(8) for x in range(8)
        for _ in range(3)))

for name in sorted(os.listdir(OUT)):
    full = os.path.join(OUT, name)
    print("%6d  %s" % (os.path.getsize(full), name))
print("seeds done ->", OUT)
