#!/usr/bin/env python3
"""Conan test_package for perl-text-diff — R34 real API usage (no empty shell).

Text::Diff is pure Perl. The verifiable artifact is lib/perl5/Text/Diff.pm
under <pkg>/. This test loads the packaged module via perl -I<lib> and
computes a real diff between two text strings — proving the module is
loadable and functional.
"""
import os
import shutil
import subprocess
import sys


def find_perl():
    p = shutil.which("perl")
    if p:
        return p
    for cand in ("/storage/Users/currentUser/usr/local/bin/perl",
                 "/data/service/hnp/bin/perl", "/usr/bin/perl"):
        if os.path.isfile(cand):
            return cand
    return None


def main():
    pkg = sys.argv[1]
    dep_pkg = sys.argv[2] if len(sys.argv) > 2 else None
    perl5 = os.path.join(pkg, "lib", "perl5")
    if not os.path.isfile(os.path.join(perl5, "Text", "Diff.pm")):
        print(f"FAIL: Text/Diff.pm not found under {perl5}", file=sys.stderr)
        return 1
    perl = find_perl()
    if not perl:
        print("FAIL: perl interpreter not found", file=sys.stderr)
        return 1

    # R34: load the packaged module and compute a real diff.
    # 需要注入依赖 perl-algorithm-diff 的 lib/perl5（Algorithm::Diff）
    # 数组引用输入（diff 的 ARRAY 分支，同 perl-algorithm-diff 先例）——
    # 避免裸字符串被当作文件名（!$type 分支）与 -e 内联转义问题。
    inc = [f"-I{perl5}"]
    if dep_pkg:
        dep_perl5 = os.path.join(dep_pkg, "lib", "perl5")
        if os.path.isdir(dep_perl5):
            inc.append(f"-I{dep_perl5}")
    perl_prog = (
        "use strict; use Text::Diff qw(diff); "
        "my $d = diff([qw(a b c)], [qw(a b d)]); "
        "print \"Text::Diff loaded, has_delta=\" . (($d =~ /-c/ and $d =~ /\\+d/) ? 1 : 0) . \"\\n\";"
    )
    r = subprocess.run([perl] + inc + ["-e", perl_prog],
                       capture_output=True, text=True)
    if r.returncode != 0:
        print(f"FAIL: perl load rc={r.returncode}: {r.stderr.strip()[:300]}",
              file=sys.stderr)
        return 1
    if "Text::Diff loaded" not in r.stdout or "has_delta=1" not in r.stdout:
        print(f"FAIL: unexpected output: {r.stdout[:200]}", file=sys.stderr)
        return 1
    print(f"OK: {r.stdout.strip()}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
