#!/usr/bin/env python3
"""鸿蒙特有测试 — bart-view cfl2png/view 在 OHOS 上的真实功能验证。

上游无任何自动化测试。本测试不做"文件存在/大小合理"这类弱断言，而是：

  * 用一个自实现的 PNG 解码器（解析 chunk + 校验 CRC + zlib 解压 + 反滤波）
    读出 cfl2png 实际写出的像素，并与**独立推算的真值**逐像素比对；
  * 真值来自上游算法（cfl2png.c/draw.c）：MAGN 灰度为
    gray = trunc(255 * clamp((scale*|v| - winlow)/(winhigh - winlow), 0, 1))，
    其中 scale = 1/max（相对窗口）或 1（-A 绝对窗口）。构造的数据集使该式
    在浮点下**逐位精确**（值取 n/256、n/255），因此可做零容差比较。

覆盖的 cfl2png 功能路径（均为真实执行被测二进制）：
  1. 绝对窗口 -A + 缩放 -z 1：256 像素零容差比对（含 x/y 方向、windowing、
     magnitude 映射、PNG 编码）；
  2. 相对窗口（默认，自动求 max）：|像素 - 真值| <= 1 且单调非减，端点 0/255；
  3. 翻转 -FZ(XY)：零容差反向比对；
  4. 色图 -CV(viridis)：低端精确等于 viridis 起点色，高端与参考色相符；
  5. 全零数据：走 max==0 -> max=1 分支，输出应为全黑不透明；
  6. 缩放：默认 -z 2 -> 32x32，-z 1 -> 16x16；
  7. 确定性：同输入两次输出逐字节一致；
  8. CLI 校验：非法窗口 (-l 0.9 -u 0.5) 必须非零退出；
  9. view(GTK3)：无 DISPLAY 下依赖栈完整加载且到达 display open。

用法: python3 test_cfl2png.py <package_bin_dir>
退出码: 0 = 全部通过；1 = 存在失败（打印失败用例名）
"""
import os
import struct
import subprocess
import sys
import tempfile
import zlib

PNG_SIG = b"\x89PNG\r\n\x1a\n"
W = 16
H = 16

_FAILED = []
_CHECKS = [0]
_PIXELS = [0]


def check(name, condition, detail=""):
    _CHECKS[0] += 1
    if condition:
        print(f"[ok]   {name}")
        return True
    print(f"[fail] {name}: {detail}")
    _FAILED.append(name)
    return False


def count_pixels(n):
    _PIXELS[0] += n


# --------------------------------------------------------------------------
# CFL dataset writer (BART .hdr = 逐行维度; .cfl = 原始 complex float)
# --------------------------------------------------------------------------
def write_cfl(folder, name, value_fn):
    with open(os.path.join(folder, name + ".hdr"), "w", encoding="utf-8") as handle:
        handle.write("# Dimensions\n%d\n%d\n" % (W, H))
    payload = bytearray()
    for y in range(H):
        for x in range(W):
            payload += struct.pack("<ff", value_fn(x, y), 0.0)
    with open(os.path.join(folder, name + ".cfl"), "wb") as handle:
        handle.write(payload)


def run_cfl2png(cfl2png, folder, name, out_name, args):
    prefix = os.path.join(folder, out_name)
    # cfl2png 用 strrchr(out_prefix, '.') 判定扩展名（非 ".png" 即报
    # "Unknown file extension."）。若以绝对路径调用，路径中任何 '.' 都会被误取为扩展名
    # （CI 的 TMPDIR 形如 ~/.cache/tmp，最后一个 '.' 落在 .cache 上）。
    # 故以相对名 + cwd=folder 调用，令参数中不含路径分隔以外的 '.'。
    result = subprocess.run(
        [cfl2png] + list(args) + [name, out_name],
        capture_output=True, text=True, cwd=folder, timeout=180)
    return result.returncode, prefix + ".png", (result.stderr or result.stdout)


# --------------------------------------------------------------------------
# 自实现 PNG 解码器：chunk 解析(校验 CRC) + zlib 解压 + 反滤波
# --------------------------------------------------------------------------
def read_png(path):
    with open(path, "rb") as handle:
        data = handle.read()
    if data[:8] != PNG_SIG:
        raise AssertionError("bad PNG signature")
    pos, idat, ihdr, seen = 8, bytearray(), None, []
    while pos < len(data):
        length = int.from_bytes(data[pos:pos + 4], "big")
        ctype = data[pos + 4:pos + 8]
        body = data[pos + 8:pos + 8 + length]
        crc = int.from_bytes(data[pos + 8 + length:pos + 12 + length], "big")
        if zlib.crc32(ctype + body) & 0xffffffff != crc:
            raise AssertionError(f"CRC mismatch in {ctype!r} chunk")
        seen.append(ctype)
        if ctype == b"IHDR":
            ihdr = body
        elif ctype == b"IDAT":
            idat += body
        elif ctype == b"IEND":
            break
        pos += 12 + length
    width = int.from_bytes(ihdr[0:4], "big")
    height = int.from_bytes(ihdr[4:8], "big")
    info = {
        "width": width,
        "height": height,
        "depth": ihdr[8],
        "color_type": ihdr[9],
        "interlace": ihdr[12],
        "chunks": seen,
    }
    bpp = {6: 4, 2: 3, 0: 1}[info["color_type"]]
    raw = zlib.decompress(bytes(idat))
    if len(raw) != height * (1 + width * bpp):
        raise AssertionError("unexpected decompressed size")
    out = bytearray()
    prev = bytearray(width * bpp)
    p = 0
    for _ in range(height):
        filt = raw[p]
        p += 1
        line = bytearray(raw[p:p + width * bpp])
        p += width * bpp
        for i in range(width * bpp):
            a = line[i - bpp] if i >= bpp else 0
            b = prev[i]
            c = prev[i - bpp] if i >= bpp else 0
            x = line[i]
            if filt == 0:
                val = x
            elif filt == 1:
                val = x + a
            elif filt == 2:
                val = x + b
            elif filt == 3:
                val = x + ((a + b) >> 1)
            elif filt == 4:
                pred = a + b - c
                pa, pb, pc = abs(pred - a), abs(pred - b), abs(pred - c)
                if pa <= pb and pa <= pc:
                    pr = a
                elif pb <= pc:
                    pr = b
                else:
                    pr = c
                val = x + pr
            else:
                raise AssertionError(f"unknown PNG filter {filt}")
            line[i] = val & 0xff
        out += line
        prev = line
    info["pixels"] = bytes(out)
    info["bpp"] = bpp
    return info


def px(img, x, y):
    off = (y * img["width"] + x) * img["bpp"]
    return tuple(img["pixels"][off:off + img["bpp"]])


# --------------------------------------------------------------------------
# 真值推算（独立于被测实现，仅依据上游算法语义）
# --------------------------------------------------------------------------
def gray_absolute(n):
    """-A 绝对窗口、数据集值 n/256 时的期望灰度（float 下逐位精确）。"""
    return (255 * n) // 256


def main():
    bindir = sys.argv[1]
    cfl2png = os.path.join(bindir, "cfl2png")
    view = os.path.join(bindir, "view")
    check("cfl2png executable", os.access(cfl2png, os.X_OK), cfl2png)
    check("view executable", os.access(view, os.X_OK), view)

    with tempfile.TemporaryDirectory(prefix="bart-view-test-") as folder:
        # 数据集 1：v = n/256（n = x + 16*y），配 -A 绝对窗口 => 真值逐位精确
        write_cfl(folder, "ramp256", lambda x, y: (x + 16 * y) / 256.0)
        rc, png, err = run_cfl2png(cfl2png, folder, "ramp256", "o_abs",
                                   ["-A", "-z", "1"])
        check("absolute-windowing conversion exits 0", rc == 0, err.strip())
        img = read_png(png)
        check("png header is 8-bit RGBA, non-interlaced, 16x16",
              img["depth"] == 8 and img["color_type"] == 6
              and img["interlace"] == 0
              and (img["width"], img["height"]) == (16, 16),
              str({k: img[k] for k in ("depth", "color_type", "interlace",
                                       "width", "height")}))
        check("png contains IHDR/IDAT/IEND chunks",
              img["chunks"][0] == b"IHDR" and img["chunks"][-1] == b"IEND"
              and b"IDAT" in img["chunks"], str(img["chunks"]))

        # T1: 256 像素零容差比对（同时验证 x/y 方向）
        bad = [(x, y, px(img, x, y), gray_absolute(x + 16 * y))
               for y in range(H) for x in range(W)
               if px(img, x, y) != (gray_absolute(x + 16 * y),) * 3 + (255,)]
        count_pixels(W * H)
        check("all 256 pixels match computed gray exactly (-A: trunc(255*n/256))",
              not bad, f"{len(bad)} mismatches, e.g. {bad[:3]}")

        # T2: 相对窗口（默认，自动求 max）：v = n/255 => max=1.0
        write_cfl(folder, "ramp255", lambda x, y: (x + 16 * y) / 255.0)
        rc, png, err = run_cfl2png(cfl2png, folder, "ramp255", "o_rel", ["-z", "1"])
        check("relative-windowing conversion exits 0", rc == 0, err.strip())
        img_rel = read_png(png)
        vals = [px(img_rel, x, y)[0] for y in range(H) for x in range(W)]
        count_pixels(len(vals))
        maxdiff = max(abs(v - n) for n, v in enumerate(vals))
        check("auto-windowing gray within 1 level of n (max=1.0 detected)",
              maxdiff <= 1, f"max diff {maxdiff}")
        check("auto-windowing gray is monotonic non-decreasing and spans 0..255",
              all(a <= b for a, b in zip(vals, vals[1:]))
              and vals[0] == 0 and vals[-1] == 255,
              f"first={vals[0]} last={vals[-1]}")
        check("auto-windowing is opaque RGB gray (R=G=B)",
              all(len(set(px(img_rel, x, y)[:3])) == 1
                  for y in range(H) for x in range(W)))
        count_pixels(W * H)

        # T3: 翻转 -FZ (XY) 零容差
        rc, png, err = run_cfl2png(cfl2png, folder, "ramp256", "o_flip",
                                   ["-A", "-z", "1", "-FZ"])
        check("flip (XY) conversion exits 0", rc == 0, err.strip())
        img_flip = read_png(png)
        bad = [(x, y) for y in range(H) for x in range(W)
               if px(img_flip, x, y)
               != (gray_absolute((W - 1 - x) + W * (H - 1 - y)),) * 3 + (255,)]
        count_pixels(W * H)
        check("flip XY maps out(x,y) = src(15-x, 15-y) exactly", not bad,
              f"{len(bad)} mismatches, e.g. {bad[:3]}")

        # T4: 色图 -CV (viridis)
        rc, png, err = run_cfl2png(cfl2png, folder, "ramp256", "o_viridis",
                                   ["-A", "-z", "1", "-CV"])
        check("viridis colormap conversion exits 0", rc == 0, err.strip())
        img_v = read_png(png)
        low = px(img_v, 0, 0)
        high = px(img_v, W - 1, H - 1)
        mid = px(img_v, 8, 7)
        check("viridis low end is the viridis start colour (68,1,84,255)",
              low == (68, 1, 84, 255), str(low))
        check("viridis high end matches viridis reference (250,230,34,255) +-4",
              all(abs(a - b) <= 4 for a, b in zip(high, (250, 230, 34, 255))),
              str(high))
        check("viridis mid tone is a colour (channels differ)",
              len(set(mid[:3])) == 3, str(mid))
        count_pixels(3)

        # T5: 全零数据（覆盖 max==0 -> max=1 分支）
        write_cfl(folder, "zeros", lambda x, y: 0.0)
        rc, png, err = run_cfl2png(cfl2png, folder, "zeros", "o_zero", ["-A", "-z", "1"])
        check("all-zero dataset conversion exits 0", rc == 0, err.strip())
        img_z = read_png(png)
        zero_ok = all(px(img_z, x, y) == (0, 0, 0, 255)
                      for y in range(H) for x in range(W))
        count_pixels(W * H)
        check("all-zero data renders fully black and opaque", zero_ok)

        # T6: 缩放
        rc, png, _ = run_cfl2png(cfl2png, folder, "ramp255", "o_zoom", [])
        img_zoom = read_png(png)
        check("default zoom 2 produces 32x32", rc == 0
              and (img_zoom["width"], img_zoom["height"]) == (W * 2, H * 2),
              f"{img_zoom['width']}x{img_zoom['height']}")

        # T7: 确定性
        _, png_a, _ = run_cfl2png(cfl2png, folder, "ramp256", "o_det1", ["-A", "-z", "1"])
        _, png_b, _ = run_cfl2png(cfl2png, folder, "ramp256", "o_det2", ["-A", "-z", "1"])
        check("repeated conversion is byte-identical",
              open(png_a, "rb").read() == open(png_b, "rb").read())

        # T8: CLI 校验（非法窗口必须非零退出）
        rc, _, _ = run_cfl2png(cfl2png, folder, "ramp256", "o_bad",
                               ["-l", "0.9", "-u", "0.5"])
        check("invalid window (lower > upper) is rejected (non-zero exit)",
              rc != 0, f"exit={rc}")

    # T9: view 依赖栈（无 DISPLAY 环境）
    result = subprocess.run([view], capture_output=True, text=True, timeout=180)
    combined = result.stdout + result.stderr
    check("view loads without missing shared library",
          "Error loading shared library" not in combined, combined.strip())
    check("view GTK3 init reaches display open",
          "cannot open display" in combined, combined.strip())

    print("-" * 64)
    print(f"assertions: {_CHECKS[0]} checks + {_PIXELS[0]} pixel comparisons")
    if _FAILED:
        print(f"FAILED ({len(_FAILED)}): " + ", ".join(_FAILED))
        return 1
    print("ALL TESTS PASSED")
    return 0


if __name__ == "__main__":
    sys.exit(main())
