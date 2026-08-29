#!/usr/bin/env python3
"""libdebian-installer consumer test (R34): real API call via compile+link+run.

Fixes AI review P2 (empty-shell test — only checked .a exists, never called
any API): now compiles a C program that includes <debian-installer/mem.h>
and <debian-installer/hash.h> and actually calls di_malloc/di_free and
di_hash_table_new, links against libdebian-installer.a + libsystem.a, runs
it and verifies output. P3: checks lib dir exists before listing.
"""
import os
import subprocess
import sys
import tempfile

SMOKE_C = r'''
#include <debian-installer/mem.h>
#include <debian-installer/hash.h>
#include <stdio.h>

int main(void) {
    /* real API usage: di_malloc / di_free (mem.h) */
    void *p = di_malloc(16);
    if (!p) { printf("FAIL: di_malloc returned NULL\n"); return 1; }
    di_free(p);
    /* real API usage: di_hash_table_new (hash.h) */
    di_hash_table *t = di_hash_table_new(di_rstring_hash, NULL);
    if (!t) { printf("FAIL: di_hash_table_new returned NULL\n"); return 1; }
    printf("OK: libdebian-installer di_malloc/di_free/di_hash_table_new work\n");
    return 0;
}
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    inc = os.path.join(pkg, "include")
    lib = os.path.join(pkg, "lib")
    if not os.path.isdir(lib):
        print(f"FAIL: lib dir missing: {lib}", file=sys.stderr)
        return 1
    # P2 修复：真实 API 调用——编译 C 程序链接 libdebian-installer.a
    # + libsystem.a（di_malloc/di_hash_table_new 符号实测在
    # libdebian-installer.a），编译产物写入临时目录（不污染包目录）
    tmpdir = tempfile.mkdtemp(prefix="ldi-smoke-")
    src = os.path.join(tmpdir, "smoke.c")
    binp = os.path.join(tmpdir, "smoke")
    try:
        with open(src, "w") as f:
            f.write(SMOKE_C)
        r = subprocess.run(
            ["/data/service/hnp/bin/clang", src, "-o", binp,
             f"-I{inc}",
             os.path.join(lib, "libdebian-installer.a"),
             os.path.join(lib, "libsystem.a")],
            capture_output=True, text=True)
        if r.returncode != 0:
            print(f"FAIL: compile smoke: {r.stderr}", file=sys.stderr)
            return 1
        r = subprocess.run([binp], capture_output=True, text=True)
        if r.returncode != 0:
            print(f"FAIL: run smoke: {r.stderr}", file=sys.stderr)
            return 1
        print(r.stdout.strip())
    finally:
        import shutil
        shutil.rmtree(tmpdir, ignore_errors=True)
    print("OK: libdebian-installer real API compile+link+run works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
