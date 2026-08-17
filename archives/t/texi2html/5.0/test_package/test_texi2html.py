#!/usr/bin/env python3
"""test_package — texi2html 消费验证（L0d: test() 必须 self.run）。

验证 bin/texi2html 主脚本存在 + perl -c 语法检查（Perl 工具 headless 可运行）。
"""
import os
import subprocess
import sys


def main():
    pkg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PACKAGE_FOLDER", "")
    perl_pkg = sys.argv[2] if len(sys.argv) > 2 else ""
    bins = os.path.join(pkg, "bin")
    script = None
    for name in ("texi2html", "texi2html.pl", "texi2html.py"):
        cand = os.path.join(bins, name)
        if os.path.isfile(cand):
            script = cand
            break
    if script is None:
        print(f"FAIL: no texi2html script in {bins}")
        return 1
    print(f"OK: texi2html script present: {os.path.basename(script)}")
    # perl -c 语法检查（PERL5LIB 注入 perl 制品 lib）
    env = dict(os.environ)
    perl5lib = os.path.join(pkg, "..", "..", "..", "perl", "5.42.2", "lib", "perl5", "5.42.2")
    if os.path.isdir(perl5lib):
        env["PERL5LIB"] = perl5lib + os.pathsep + env.get("PERL5LIB", "")
    perl_exe = os.path.join(perl_pkg, "bin", "perl") if perl_pkg else "perl"
    if not os.path.isfile(perl_exe) and perl_pkg:
        # perl 制品 bin 名可能是 perl5.42.2 或 perl（探测）
        for cand in ("perl", "perl5.42.2"):
            c = os.path.join(perl_pkg, "bin", cand)
            if os.path.isfile(c):
                perl_exe = c
                break
    try:
        r = subprocess.run([perl_exe, "-c", script], capture_output=True,
                           text=True, timeout=60, env=env)
        out = r.stdout or r.stderr or ""
        if r.returncode == 0 and "syntax OK" in out:
            print("OK: perl -c syntax OK")
        else:
            print(f"FAIL: perl -c rc={r.returncode}: {(out or '')[:200]}")
            return 1
    except FileNotFoundError:
        print(f"FAIL: perl not found ({perl_exe})")
        return 1
    except subprocess.TimeoutExpired:
        print("FAIL: perl -c timed out")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
