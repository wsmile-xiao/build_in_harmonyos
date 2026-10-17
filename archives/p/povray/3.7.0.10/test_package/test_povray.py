#!/usr/bin/env python3
"""povray 3.7.0.10 test_package 独立测试驱动。

消费者视角验证（L1 级，R34 实质断言），由 conanfile.py test() 经 self.run()
调用（CI L0d 要求 test() 内有 self.run；L0c 按扩展名认测试源文件，
conanfile.py 本身不计，故断言逻辑放本脚本）。

验证内容（14 项断言）：
  1. banner：`povray --version` 输出含 "Persistence of Vision"（上游品牌行，
     与编译期 COMPILED_BY 一并验证二进制完整可执行）
  2. 真实渲染：test.pov（相机+光源+棋盘格平面+球，#include "colors.inc"
     场景库）→ 64x64 PNG
     - 断言进程退出码 0（解析/渲染失败时 povray 返回 1）
     - 断言 PNG 魔数 \\x89PNG\\r\\x1a\\n + IHDR 64x64 + bit_depth 8 + color_type 2(RGB)
     - 断言渲染统计行 "Trace Time" 出现（渲染引擎真实运行）
     - +L 指向包内 share/povray-3.7/include —— 同时验证场景库安装布局

用法: test_povray.py <povray_bin> <test_pov> <include_dir>
所有输出（banner/渲染产物/日志）写进临时目录，不污染源目录；临时目录在
finally 中清理（review 188095868：mkdtemp 泄漏修复）。子进程带超时，
防止异常时 CI 挂起（review 188095868）。
"""
import os
import shutil
import struct
import subprocess
import sys
import tempfile

BANNER_TIMEOUT = 120   # 秒；banner 实测 <1s，CI 冷启动留余量
RENDER_TIMEOUT = 300   # 秒；64x64 渲染实测 <0.1s，留足余量


def main():
    if len(sys.argv) != 4:
        sys.stderr.write("usage: test_povray.py <povray_bin> <test_pov> <include_dir>\n")
        return 2
    povray_bin, test_pov, include_dir = sys.argv[1], sys.argv[2], sys.argv[3]

    # ---- 包布局预检（断言 1/2）-----------------------------------------
    assert os.path.isfile(povray_bin), "bin/povray not found in package"
    colors_inc = os.path.join(include_dir, "colors.inc")
    assert os.path.isfile(colors_inc), \
        "share/povray-3.7/include/colors.inc not found in package"

    # 所有输出写进临时目录（test_type=explicit 下工作目录即 test_package/
    # 源目录，直接落盘会污染归档目录——E600 教训）
    workdir = tempfile.mkdtemp(prefix="povray_test_")
    try:
        return run_tests(povray_bin, test_pov, include_dir, workdir)
    finally:
        shutil.rmtree(workdir, ignore_errors=True)


def run_tests(povray_bin, test_pov, include_dir, workdir):
    # ---- Test 1: banner（断言 3/4）--------------------------------------
    with open(os.path.join(workdir, "banner.txt"), "wb") as out:
        rc = subprocess.call([povray_bin, "--version"], stdout=out, stderr=out,
                             timeout=BANNER_TIMEOUT)
    assert rc == 0, "povray --version exited %d" % rc
    with open(os.path.join(workdir, "banner.txt"), "r", errors="replace") as f:
        banner = f.read()
    assert "Persistence of Vision" in banner, \
        "banner missing 'Persistence of Vision':\n%s" % banner
    assert "3.7.0.10" in banner, "banner missing version 3.7.0.10:\n%s" % banner
    print("[test] banner OK (POV-Ray 3.7.0.10, Persistence of Vision)")

    # ---- Test 2: 真实渲染（断言 5-14）------------------------------------
    # 解析/渲染失败时 povray 返回 1（本机验证：broken 场景 RC=1 无产物）
    render_log_path = os.path.join(workdir, "render.log")
    with open(render_log_path, "wb") as out:
        rc = subprocess.call(
            [povray_bin,
             "+I" + test_pov,
             "+O" + os.path.join(workdir, "test.png"),
             "+W64", "+H64", "-D",
             "-L" + include_dir],
            stdout=out, stderr=out, timeout=RENDER_TIMEOUT)
    assert rc == 0, "render exited %d (parse/render failure):" % rc

    png_path = os.path.join(workdir, "test.png")
    assert os.path.isfile(png_path), "render produced no test.png"
    with open(png_path, "rb") as f:
        png = f.read()
    # PNG 魔数
    assert png[:8] == b"\x89PNG\x0d\x0a\x1a\x0a", "bad PNG magic: %r" % png[:8]
    # IHDR: 第一个 chunk 必须是 IHDR，宽高 64x64
    assert png[12:16] == b"IHDR", "first chunk is not IHDR"
    width, height, bit_depth, color_type = struct.unpack(">IIBB", png[16:26])
    assert (width, height) == (64, 64), "IHDR size != 64x64: %dx%d" % (width, height)
    assert bit_depth == 8, "bit_depth != 8: %d" % bit_depth
    assert color_type == 2, "color_type != 2 (truecolor RGB): %d" % color_type

    with open(render_log_path, "r", errors="replace") as f:
        render_log = f.read()
    assert "Trace Time" in render_log, "render.log missing 'Trace Time' stat line"
    assert "Parse Error" not in render_log, "Parse Error in render.log"

    print("[test] render OK: PNG 64x64 RGB8 (%d bytes), Trace Time stat present"
          % len(png))
    print("HMBS_TEST_PACKAGE_RESULT: PASS povray/3.7.0.10 "
          "(banner=Persistence of Vision/3.7.0.10, render=64x64 PNG magic+IHDR+RGB8, "
          "scene library=colors.inc resolved from package share dir)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
