#!/usr/bin/env python3
"""cvsweb 3.0.6 consumer test — pure Perl CGI smoke verification.

Checks the installed package: cvsweb.cgi exists, is a Perl script with a
taint-mode shebang, and passes `perl -T -c` syntax check with PERL5LIB
pointing at the bundled IPC::Run/URI modules. Exits non-zero on failure.
"""
import os
import subprocess
import sys


def main():
    pkg_root = sys.argv[1] if len(sys.argv) > 1 else "."
    failures = 0

    cgi = os.path.join(pkg_root, "libexec", "cvsweb", "cvsweb.cgi")
    if not os.path.isfile(cgi):
        print("[FAIL] %s missing" % cgi)
        return 1
    with open(cgi, "rt", encoding="utf-8", errors="replace") as f:
        shebang = f.readline().strip()
    if not shebang.startswith("#!"):
        print("[FAIL] cvsweb.cgi has no shebang")
        failures += 1
    elif "-T" not in shebang:
        print("[FAIL] cvsweb.cgi shebang lacks taint mode (-T): %s" % shebang)
        failures += 1
    else:
        print("[ok] cvsweb.cgi shebang: %s" % shebang)

    moddir = os.path.join(pkg_root, "libexec", "cvsweb", "perl-lib")
    if not os.path.isdir(moddir):
        print("[FAIL] perl-lib (%s) missing (bundled IPC::Run/URI)" % moddir)
        failures += 1
    else:
        ipc = os.path.join(moddir, "IPC", "Run.pm")
        uri = os.path.join(moddir, "URI", "Escape.pm")
        if not (os.path.isfile(ipc) and os.path.isfile(uri)):
            print("[FAIL] bundled modules missing (IPC/Run.pm or URI/Escape.pm)")
            failures += 1
        else:
            print("[ok] bundled perl modules present (IPC::Run, URI::Escape)")

    # perl -T -c syntax self-check (taint mode: use -I, PERL5LIB is ignored).
    # OHOS perl 位于 /data/service/hnp/bin/perl（不在标准 PATH，atool 先例），
    # CI Worker 上 os.environ.get("PERL") 未设置且 PATH 无 perl，必须用绝对路径。
    perl = os.environ.get("PERL") or "/data/service/hnp/bin/perl"
    cmd = [perl, "-T", "-I", moddir, "-c", cgi]
    proc = subprocess.run(cmd, capture_output=True, text=True)
    if proc.returncode != 0:
        print("[FAIL] perl -T -c syntax check failed:\n%s" % proc.stderr.strip())
        failures += 1
    else:
        print("[ok] perl -T -c syntax OK")

    if failures:
        print("cvsweb: %d assertion(s) failed" % failures)
        return 1
    print("cvsweb package OK")
    return 0


if __name__ == "__main__":
    sys.exit(main())
