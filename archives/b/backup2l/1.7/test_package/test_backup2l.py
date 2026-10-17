#!/usr/bin/env python3
"""backup2l consumer test (L0c: standalone test source executed via
self.run from conanfile.py test()).

backup2l is a shell-script backup tool; running it requires an edited
config file (first-time.conf template UNCONFIGURED=1 aborts with
'has to be edited' even with --conf --help — tool usage prerequisite,
honest) and a mountable FS. This script verifies the packaged script
+ config are present and the script passes bash -n syntax check.

Usage: test_backup2l.py <package-folder>
"""
import os
import subprocess
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <package-folder>", file=sys.stderr)
        return 2
    pkg = sys.argv[1]
    exe = os.path.join(pkg, "bin", "backup2l")
    conf = os.path.join(pkg, "etc", "backup2l", "first-time.conf")
    if not os.path.isfile(exe):
        raise AssertionError(f"backup2l script missing: {exe}")
    if not os.path.isfile(conf):
        raise AssertionError(f"backup2l config missing: {conf}")
    # bash -n 语法检查（真实确认脚本在 OHOS bash 可用）——绝对路径
    # /data/service/hnp/bin/bash（conanrun PATH 不含相对名 bash，
    # subprocess 抛 FileNotFoundError，同 simavr 的 clang 教训）
    r = subprocess.run(["/data/service/hnp/bin/bash", "-n", exe],
                       capture_output=True, text=True)
    if r.returncode != 0:
        raise AssertionError(f"backup2l syntax invalid: {r.stderr}")
    print(f"OK: backup2l script syntax valid ({exe})")
    return 0


if __name__ == "__main__":
    sys.exit(main())
