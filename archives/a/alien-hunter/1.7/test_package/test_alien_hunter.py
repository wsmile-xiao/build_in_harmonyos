#!/usr/bin/env python3
"""test_package — alien-hunter 消费验证（L0d: test() 必须 self.run）。

真正运行 alien_hunter.pl + 自带 demoSeq.dna（IVOM 预测，纯 Perl 主功能）：
- 正确参数：-file_genome <dna> -output <前缀>（alien_hunter.pl GetOptions 需
  file_genome 与 output，缺任一则只打印 help 不生成输出）
- PERL5LIB 注入制品 lib 目录（perl 制品 @INC 为构建时绝对路径，需注入才能
  加载 PAI_scripts 模块与 perl core 模块）
- 断言 subprocess returncode == 0
- 断言预测输出文件（<output>.sco 分数 / <output>.plot / <output> EMBL）确实生成

可选 Java 边界优化（-c）因 OHOS 无 Java 不触发。
"""
import os
import subprocess
import sys


def main():
    pkg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PACKAGE_FOLDER", "")
    bindir = os.path.join(pkg, "bin")
    datadir = os.path.join(pkg, "share", "alien-hunter")
    libdir = os.path.join(pkg, "lib")
    pl = os.path.join(bindir, "alien_hunter.pl")
    demo = os.path.join(datadir, "demoSeq.dna")
    for f in (pl, demo):
        if not os.path.isfile(f):
            print(f"FAIL: missing {f}")
            return 1

    # 在可写临时目录运行（预测输出生成在工作目录）
    workdir = os.path.join(os.path.dirname(os.path.abspath(pl)), "..", "tmp")
    os.makedirs(workdir, exist_ok=True)
    env = dict(os.environ)
    # PERL5LIB 注入制品 lib（含 PAI_scripts 模块），否则 perl 加载失败
    env["PERL5LIB"] = libdir + os.pathsep + env.get("PERL5LIB", "")
    env["TMPDIR"] = workdir
    out_prefix = os.path.join(workdir, "test_out")

    try:
        r = subprocess.run(
            ["perl", pl, "-file_genome", demo, "-output", out_prefix],
            capture_output=True, text=True, timeout=600,
            env=env, cwd=workdir,
        )
    except FileNotFoundError:
        print("FAIL: perl not found")
        return 1
    except subprocess.TimeoutExpired:
        print("FAIL: alien_hunter.pl timed out")
        return 1

    if r.returncode != 0:
        print(f"FAIL: alien_hunter.pl exit {r.returncode}")
        print((r.stdout or "")[-800:])
        print((r.stderr or "")[-800:])
        return 1

    # 断言预测输出文件生成（alien_hunter 输出：<prefix>.sco 分数 / .plot / EMBL）
    outputs = []
    for suf in (".sco", ".plot", ".hmm", ""):
        fn = out_prefix + suf
        if os.path.isfile(fn) and os.path.getsize(fn) > 0:
            outputs.append(fn)
    if not outputs:
        print(f"FAIL: no prediction output generated in {workdir}")
        print((r.stdout or "")[-800:])
        return 1

    print(f"OK: alien_hunter.pl ran (IVOM prediction) -> outputs: "
          f"{[os.path.basename(o) for o in outputs]}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
