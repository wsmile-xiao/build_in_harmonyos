#!/usr/bin/env python3
"""gengen 真实消费者闭环（工具型包，只跑 --help / 只打印 / 只查文件存在不合格）：

  ① 用 gengen 从最小 .cc_skel 骨架生成 demo.h（工具本身可执行、生成正确）
  ② 断言 demo.h 含 demo_gen_class / set_value / set_flag / generate_demo 核心契约
  ③ 把生成的 demo.h 与消费者 main 一起编译成可执行文件（生成代码可编译）
  ④ 运行消费者，断言 stdout 与期望文本逐字一致（生成代码行为正确）

期望输出已在设备上实证（clang 15 / aarch64 OHOS）：
  demo begin\n  value=42\n  flag=yes\ndemo end\n
"""
import os
import shutil
import subprocess
import sys
import tempfile

SKEL = """demo begin
  value=@value@
@IF@ flag @THEN@
  flag=yes
@ELSE@
  flag=no
@ENDIF@
demo end
"""

MAIN = r"""
#include <sstream>
#include <iostream>
#include "demo.h"

int main() {
  demo_gen_class g;
  g.set_value("42");
  g.set_flag(true);
  std::ostringstream out;
  g.generate_demo(out);
  std::cout << out.str();
  return 0;
}
"""

EXPECTED = "demo begin\n  value=42\n  flag=yes\ndemo end\n"


def find_cxx():
    """优先环境 CXX（conan 工具链注入），再 PATH，最后设备固定路径。"""
    cxx = os.environ.get("CXX")
    if cxx:
        resolved = shutil.which(cxx) if os.path.sep not in cxx else (
            cxx if os.path.isfile(cxx) else None)
        if resolved:
            return resolved
    for name in ("clang++", "c++", "g++"):
        p = shutil.which(name)
        if p:
            return p
    fallback = "/data/service/hnp/bin/clang++"
    return fallback if os.path.isfile(fallback) else None


def main(argv):
    if len(argv) < 2:
        print("用法: test.py <gengen 可执行文件>", file=sys.stderr)
        return 2
    exe = argv[1]
    if not os.path.isfile(exe):
        print("[FAIL] 缺可执行文件: %s" % exe)
        return 1
    d = tempfile.mkdtemp()
    skel = os.path.join(d, "demo.cc_skel")
    with open(skel, "w", encoding="utf-8") as f:
        f.write(SKEL)
    header = os.path.join(d, "demo.h")
    failures = 0

    # ① 工具真实生成
    gen = subprocess.run([exe, "--no-gen-version", "-i", skel,
                          "--file-name", header, "--gen-name", "demo"],
                         capture_output=True, text=True, timeout=300)
    if gen.returncode != 0:
        print("[FAIL] gengen 退出码 %d: %s" % (gen.returncode, (gen.stderr or "")[-400:]))
        return 1
    if not os.path.isfile(header):
        print("[FAIL] 没有生成 demo.h")
        return 1
    print("[PASS] gengen 由 .cc_skel 生成 demo.h")

    # ② 生成内容契约
    with open(header, encoding="utf-8", errors="replace") as f:
        ht = f.read()
    for needle in ("class demo_gen_class", "void set_value",
                   "void set_flag", "generate_demo"):
        if needle not in ht:
            print("[FAIL] demo.h 里没有 %s" % needle)
            failures += 1
        else:
            print("[PASS] demo.h 含 %s" % needle)

    # ③ 生成代码必须可编译（和消费者 main 一起）
    main_cc = os.path.join(d, "main.cc")
    with open(main_cc, "w", encoding="utf-8") as f:
        f.write(MAIN)
    cxx = find_cxx()
    if not cxx:
        print("[FAIL] 找不到 C++ 编译器")
        return 1
    consumer = os.path.join(d, "consumer")
    comp = subprocess.run([cxx, "-I", d, "-o", consumer, main_cc],
                          capture_output=True, text=True, timeout=300)
    if comp.returncode != 0:
        print("[FAIL] 生成代码编译失败: %s" % (comp.stderr or "")[-400:])
        return 1
    print("[PASS] 生成的 demo.h 可编译（%s）" % cxx)

    # ④ 生成代码行为断言
    run = subprocess.run([consumer], capture_output=True, text=True, timeout=300)
    if run.returncode != 0:
        print("[FAIL] 消费者退出码 %d" % run.returncode)
        failures += 1
    elif run.stdout != EXPECTED:
        print("[FAIL] 输出不匹配\n期望: %r\n实际: %r" % (EXPECTED, run.stdout))
        failures += 1
    else:
        print("[PASS] 生成代码行为正确（输出逐字一致）")

    print("gengen 消费者闭环: 7 项断言，失败 %d 项" % failures)
    return 1 if failures else 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))
