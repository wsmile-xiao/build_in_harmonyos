#!/usr/bin/env python3
"""tachyon 真实渲染断言（独立可跑：`python3 test.py <bin目录>`）。

为什么断言 PNG 而不是"跑起来不报错"：`-format PNG` 这个分支在源码里被
`#if defined(USEPNG)` 包着（demosrc/getargs.c:559）。若 libpng 没接上，
tachyon **不会报错**，只会打印一行 "Unknown/Unsupported Image Format"
然后**默默回退成 Targa**。于是"输出文件是不是真的 PNG"正好是 libpng
有没有真链上的判据 —— 比任何 dlopen 探针都硬。

三条断言：① 没出现格式回退提示 ② 前 8 字节是 PNG 魔数 ③ IHDR 里的宽高就是我们要的。
"""
import os
import struct
import subprocess
import sys
import tempfile

RES = 64

SCENE = """BEGIN_SCENE
  RESOLUTION {res} {res}
CAMERA
  ZOOM 1.0
  ASPECTRATIO 1.0
  ANTIALIASING 0
  RAYDEPTH 4
  CENTER 0.0 0.0 -5.0
  VIEWDIR 0.0 0.0 1.0
  UPDIR 0.0 1.0 0.0
END_CAMERA
LIGHT
  CENTER -3.0 3.0 -3.0
  RAD 0.2
  COLOR 1.0 1.0 1.0
SPHERE
  CENTER 0.0 0.0 0.0
  RAD 1.0
  TEXTURE
    AMBIENT 0.1 DIFFUSE 0.9 SPECULAR 0.0 OPACITY 1.0
    COLOR 1.0 0.0 0.0
    TEXFUNC 0
END_SCENE
""".format(res=RES)


def main(argv):
    if len(argv) < 2:
        print("用法: test.py <bin目录>", file=sys.stderr)
        return 2
    exe = os.path.join(argv[1], "tachyon")
    if not os.path.isfile(exe):
        print("[FAIL] 缺可执行文件: %s" % exe)
        return 1

    tmpdir = tempfile.mkdtemp()
    scene = os.path.join(tmpdir, "scene.dat")
    out_png = os.path.join(tmpdir, "out.png")
    with open(scene, "w", encoding="utf-8") as f:
        f.write(SCENE)

    # 绝对路径调用：这份 musl 上的 exec 不做 PATH 查找，裸名会 ENOENT
    proc = subprocess.run([exe, scene, "-format", "PNG", "-o", out_png, "-numthreads", "1"],
                          capture_output=True, text=True, timeout=600)
    print((proc.stdout or "")[-600:])
    if proc.returncode != 0:
        # 典型症状：一串 `png_xxx: symbol not found` —— 那是 libpng16.so.16
        # **没被找到**（LD_LIBRARY_PATH 里没有它的目录），不是版本不对。
        print("[FAIL] 渲染失败(%d): %s" % (proc.returncode, (proc.stderr or "")[-600:]))
        return 1
    if "Unknown/Unsupported Image Format" in (proc.stdout or ""):
        print("[FAIL] tachyon 不认 PNG 格式 —— USEPNG 没生效 / libpng 没链上")
        return 1
    if not os.path.isfile(out_png):
        print("[FAIL] 没产出图像文件")
        return 1

    with open(out_png, "rb") as f:
        head = f.read(24)
    if head[:8] != b"\x89PNG\r\n\x1a\n":
        print("[FAIL] 产物不是 PNG（前 8 字节 %r）—— 多半静默回退成了 Targa" % head[:8])
        return 1
    if head[12:16] != b"IHDR":
        print("[FAIL] PNG 缺 IHDR 块")
        return 1
    width, height = struct.unpack(">II", head[16:24])
    if (width, height) != (RES, RES):
        print("[FAIL] PNG 尺寸应为 %dx%d，实得 %dx%d" % (RES, RES, width, height))
        return 1
    size = os.path.getsize(out_png)
    if size < 200:
        print("[FAIL] PNG 只有 %d 字节，像是空图" % size)
        return 1
    print("[PASS] tachyon 渲染出 %dx%d PNG（%d 字节），3 条断言全部通过" % (width, height, size))
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
