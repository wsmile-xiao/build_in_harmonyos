#!/usr/bin/env python3
"""消费测试：验证 cct 1.0.0 安装布局 + 真实计算 + 上游测试实跑。

cct（Sife-shuo/cct）是 C/C++ 进制/位运算 CLI 计算工具，交互式
无限循环（while(true) 等 stdin 输入，EOF 不退出——系统级交互模式
如实记录）。本测试验证：
1. bin/cct 可执行文件存在
2. cct 喂真实命令 "d 2 10 10100011"（二进制转十进制）真实计算
   ——输出含 [ Out ] >> 163（实测确认）；交互式不退出属预期
3. 上游 test/test.cpp 实跑（_cmd_parse 解析 "d 2 10 10100011"）
终态由各检查结果推导：任一 FAIL 即 exit 1，全部 PASS 才 "ALL PASS"。
"""
import os
import shutil
import subprocess
import sys

PASS = "PASS:"
NOTE = "NOTE:"
FAIL = "FAIL:"


def main():
    pkg_folder = sys.argv[1]
    bindir = os.path.join(pkg_folder, "bin")
    failures = 0

    # 1. bin/cct 可执行文件存在
    cct = os.path.join(bindir, "cct")
    if not os.path.isfile(cct) or not os.access(cct, os.X_OK):
        print(f"{FAIL} bin/cct 不存在或不可执行")
        sys.exit(1)
    print(f"{PASS} bin/cct 可执行文件存在")

    # 2. cct 喂真实命令 "d 2 10 10100011"（二进制→十进制）
    #    交互式循环不退出（EOF 后持续等输入）——短超时 + 检查输出
    try:
        r = subprocess.run([cct], capture_output=True, text=True, timeout=5,
                           input="d 2 10 10100011\n")
    except subprocess.TimeoutExpired as e:
        # 交互式 CLI 不退出属预期——取已输出内容
        out = (e.stdout or b"").decode("utf-8", errors="replace") if isinstance(e.stdout, bytes) else (e.stdout or "")
    else:
        out = (r.stdout or "") + (r.stderr or "")
    if "163" in out:
        print(f"{PASS} cct 真实计算二进制 10100011 → 163（输出含 [ Out ] >> 163）")
    else:
        # aireview P2 修复：计算错误必须 FAIL（真实回归信号）
        print(f"{FAIL} cct 计算输出异常（未含 163）")
        print(out[:200])
        failures += 1

    # 3. 上游 test/test.cpp 实跑（_cmd_parse 解析）
    test_dir = os.path.dirname(os.path.abspath(__file__))
    src = os.path.join(test_dir, "test_upstream.cpp")
    if not os.path.isfile(src):
        print(f"{NOTE} 上游 test_upstream.cpp 不在 test_package 内——跳过（0/0 如实）")
    else:
        cc = ""
        for cand in ("/data/service/hnp/bin/clang++",
                     "/storage/Users/currentUser/usr/local/bin/clang++",
                     os.environ.get("CXX") or "",
                     shutil.which("clang++") or ""):
            if cand and os.path.isfile(cand):
                cc = cand
                break
        if not cc:
            print(f"{NOTE} clang++ 不在 PATH——上游 test.cpp 跳过")
        else:
            out_bin = os.path.join(test_dir, "test_upstream.out")
            r = subprocess.run([cc, "-std=c++17", src, "-o", out_bin],
                               capture_output=True, text=True, timeout=120)
            if r.returncode != 0:
                # aireview P2 修复：上游测试编译失败须 FAIL（真实回归）
                print(f"{FAIL} 上游 test.cpp 编译失败（rc={r.returncode}）")
                print((r.stderr or "")[:200])
                failures += 1
            else:
                r2 = subprocess.run([out_bin], capture_output=True, text=True,
                                    timeout=30)
                out2 = (r2.stdout or "") + (r2.stderr or "")
                if "Printv" in out2 and "10100011" in out2:
                    print(f"{PASS} 上游 test.cpp 实跑通过（_cmd_parse 输出: {out2.strip()[:80]}）")
                else:
                    # aireview P2 修复：输出异常须 FAIL（真实回归）
                    print(f"{FAIL} 上游 test.cpp 输出异常（rc={r2.returncode}）")
                    print(out2[:200])
                    failures += 1

    if failures > 0:
        print(f"{FAIL} {failures} 项检查失败")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
