#!/usr/bin/env python3
"""odiff 4.5.0 consumer smoke test — 真实执行包内 bin/odiff 做图像对比。

- 生成两张相同 BMP（纯色）与两张不同 BMP（改一个像素），
- 相同图对比期望退出码 0（match）；
- 不同图对比期望退出码 22（pixel differences)，并校验 diff 输出文件生成且非空。
R34 反空壳：真实调用被测包二进制并校验输出与退出码。
"""
import os
import subprocess
import struct
import sys


def make_bmp(path, width, height, color):
    """生成 24-bit BMP（54 字节头 + BGR 像素，行按 4 字节对齐、自底向上）。"""
    row_size = (width * 3 + 3) // 4 * 4
    image_size = row_size * height
    file_size = 54 + image_size

    def bgr(c):
        return bytes((c[2], c[1], c[0]))

    with open(path, "wb") as f:
        f.write(b"BM")
        f.write(struct.pack("<IHHI", file_size, 0, 0, 54))
        f.write(struct.pack("<IiiHHIIiiII", 40, width, height, 1, 24,
                            0, image_size, 2835, 2835, 0, 0))
        pixel = bgr(color)
        for _ in range(height):
            f.write(pixel * width)
            f.write(b"\x00" * (row_size - width * 3))


def run_odiff(odiff, *args):
    """运行 odiff，返回 (returncode, stdout, stderr)。"""
    proc = subprocess.run([odiff, *args], capture_output=True, text=True)
    return proc.returncode, proc.stdout, proc.stderr


def main():
    if len(sys.argv) != 3:
        print("usage: test_odiff.py <odiff-binary> <workdir>")
        return 2
    odiff = sys.argv[1]
    workdir = sys.argv[2]
    os.makedirs(workdir, exist_ok=True)

    if not os.path.exists(odiff):
        print(f"FAIL: odiff binary not found: {odiff}")
        return 1

    # 1. --version / --help 冒烟
    # odiff 的 --version/--help 通过 Zig std.debug.print（写 stderr）输出，
    # 故合并检查 stdout+stderr。
    rc, out, err = run_odiff(odiff, "--version")
    if rc != 0:
        print(f"FAIL: odiff --version exited {rc}; {err}")
        return 1
    if not (out + err).strip():
        print("FAIL: odiff --version printed nothing (stdout+stderr)")
        return 1

    rc, out, err = run_odiff(odiff, "--help")
    if rc != 0:
        print(f"FAIL: odiff --help exited {rc}; {err}")
        return 1
    if "Usage" not in (out + err):
        print("FAIL: odiff --help does not show usage")
        return 1

    # 2. 两张相同图 → 期望退出码 0（match），无 diff 输出
    #    注：odiff 在 diff_count==0（identical）时直接退出 0，不会调用 saveImage，
    #    故此处 diff 输出路径不会被真正写入；仍用 .png 以符合「odiff v4.5.0 仅
    #    支持 .png 输出」的契约（与下方不同图对比一致）。
    img_a = os.path.join(workdir, "a.bmp")
    make_bmp(img_a, 4, 4, (200, 100, 50))
    rc, out, err = run_odiff(odiff, img_a, img_a, os.path.join(workdir, "same-diff.png"))
    if rc != 0:
        print(f"FAIL: identical images comparison exited {rc} (expected 0); {err}")
        return 1

    # 3. 两张不同图 → 期望退出码 22（pixel differences），并产生非空 diff 输出
    img_b = os.path.join(workdir, "b.bmp")
    make_bmp(img_b, 4, 4, (200, 100, 255))  # 最后一个通道不同
    # odiff v4.5.0 的 saveImageWithFormat 仅支持 .png 输出（其余返回
    # error.UnsupportedFormat），故 diff 输出扩展名用 .png。
    diff_out = os.path.join(workdir, "diff.png")
    rc, out, err = run_odiff(odiff, img_a, img_b, diff_out)
    if rc != 22:
        print(f"FAIL: different images comparison exited {rc} (expected 22); {err}")
        return 1
    if not os.path.exists(diff_out) or os.path.getsize(diff_out) == 0:
        print("FAIL: diff output image not produced or empty")
        return 1

    print("odiff smoke test PASSED (version/help, identical->0, different->22 + diff output)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
