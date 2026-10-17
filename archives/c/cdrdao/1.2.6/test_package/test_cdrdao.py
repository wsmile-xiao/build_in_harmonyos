#!/usr/bin/env python3
"""消费测试：验证 cdrdao 1.2.6 安装布局 + 真实运行 + 上游 TOC 解析用例。

cdrdao（CD 刻录工具集）是 CLI 工具（application 包）。本测试验证：
1. bin/cdrdao 可执行文件存在且可执行
2. cdrdao --version 输出含 1.2.6（真实运行验证，非空壳 R34）
3. 移植上游 testtocs/test 的 20 个 TOC 解析用例（N=20）——
   对 testtocs/*.toc 逐个执行 `cdrdao show-toc -v 9`，输出与
   testtocs/gold/*.showtoc 金标准逐字节对比（与上游 perl 脚本
   同款逻辑）。20/20 通过才 PASS，任一 FAIL 即整体失败。
终态由各检查结果推导：任一 FAIL 即 exit 1，全部 PASS 才 "ALL PASS"。
"""
import difflib
import os
import subprocess
import sys

PASS = "PASS:"
NOTE = "NOTE:"
FAIL = "FAIL:"


def main():
    pkg_folder = sys.argv[1]
    failures = 0

    # 1. bin/cdrdao 可执行文件存在且可执行
    cdrdao = os.path.join(pkg_folder, "bin", "cdrdao")
    if os.path.isfile(cdrdao) and os.access(cdrdao, os.X_OK):
        print(f"{PASS} bin/cdrdao 可执行文件存在且可执行")
    else:
        print(f"{FAIL} bin/cdrdao 不存在或不可执行")
        sys.exit(1)

    # 2. 版本真实运行验证——cdrdao 不支持 --version 命令（返回
    #    "Illegal command" rc=1），但 usage 输出含 "Cdrdao version 1.2.6"
    #    ——以输出含版本号为准（真实运行验证，非空壳 R34）
    r = subprocess.run([cdrdao, "--version"], capture_output=True,
                       text=True, encoding="utf-8", errors="replace",
                       timeout=30)
    if "1.2.6" in (r.stdout + r.stderr):
        out = (r.stdout + r.stderr).replace("\n", " ")
        print(f"{PASS} cdrdao 真实运行成功（版本 {out[:40]}）")
    else:
        print(f"{FAIL} cdrdao 运行未输出版本号（rc={r.returncode}）")
        print((r.stdout or "")[:200] + (r.stderr or "")[:200])
        failures += 1

    # 3. 上游 TOC 解析用例（N=20）——移植 testtocs/test 的对比逻辑
    #    每个 .toc 执行 show-toc -v 9，与 gold/<basename>.showtoc 逐字节
    #    对比；上游 perl 脚本同款（无金标准的 2 个 .toc 上游也跳过）
    test_dir = os.path.dirname(os.path.abspath(__file__))
    tocs_dir = os.path.join(test_dir, "testtocs")
    gold_dir = os.path.join(tocs_dir, "gold")
    if not os.path.isdir(tocs_dir) or not os.path.isdir(gold_dir):
        print(f"{FAIL} testtocs 用例目录缺失")
        sys.exit(1)

    tocs = sorted(f for f in os.listdir(tocs_dir) if f.endswith(".toc"))
    total = 0
    tocpass = 0
    for f in tocs:
        basename = f[:-4]
        gold = os.path.join(gold_dir, basename + ".showtoc")
        if not os.path.isfile(gold):
            # 无金标准的 .toc 上游脚本也跳过（not in gold → next）
            continue
        total += 1
        r = subprocess.run([cdrdao, "show-toc", "-v", "9",
                            os.path.join(tocs_dir, f)],
                           capture_output=True, text=True,
                           encoding="utf-8", errors="replace", timeout=60)
        actual = r.stdout
        with open(gold, "r", encoding="utf-8", errors="replace") as fh:
            expected = fh.read()
        if r.returncode == 0 and actual == expected:
            tocpass += 1
            print(f"{PASS} TOC 解析 {basename}（{len(expected)} 字节一致）")
        else:
            print(f"{FAIL} TOC 解析 {basename}（rc={r.returncode}，"
                  f"actual={len(actual)}B gold={len(expected)}B）")
            for line in list(difflib.unified_diff(
                    expected.splitlines(), actual.splitlines(),
                    "gold", "actual", lineterm=""))[:6]:
                print("  " + line[:120])
            failures += 1

    if total == 0:
        print(f"{FAIL} 无可用 TOC 用例")
        failures += 1
    else:
        print(f"{NOTE} 上游 TOC 解析用例：{tocpass}/{total} 通过")

    if failures > 0:
        print(f"{FAIL} {failures} 项检查失败")
        sys.exit(1)
    print("ALL PASS")
    sys.exit(0)


if __name__ == "__main__":
    main()
