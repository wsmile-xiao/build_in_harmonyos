#!/usr/bin/env python3
"""test_vulkan_headers.py — consumer test source for vulkan-headers
vulkan-sdk-1.4.357.0 (L0c).

REAL API check (R34): compile a small program including vulkan.h with
clang and assert VK_HEADER_VERSION (header completeness — the real check
for a pure header-only package).
Usage: test_vulkan_headers.py <include-dir>
"""
import os
import subprocess
import sys
import tempfile


def main():
    if len(sys.argv) < 2:
        raise SystemExit("usage: test_vulkan_headers.py <include-dir>")
    inc = sys.argv[1]
    vh = os.path.join(inc, "vulkan", "vulkan.h")
    if not os.path.isfile(vh):
        raise AssertionError(f"vulkan.h missing: {vh}")
    src = ("#include <vulkan/vulkan.h>\n"
           "#include <stdio.h>\n"
           "int main(void){ printf(\"%d\", VK_HEADER_VERSION); "
           "return VK_HEADER_VERSION > 0 ? 0 : 1; }\n")
    with tempfile.TemporaryDirectory() as tmp:
        c_file = os.path.join(tmp, "t.c")
        with open(c_file, "w") as f:
            f.write(src)
        r = subprocess.run(["/data/service/hnp/bin/clang", f"-I{inc}",
                            c_file, "-o", os.path.join(tmp, "t")],
                           capture_output=True, text=True)
        if r.returncode != 0:
            sys.stderr.write(r.stderr or "")
            raise SystemExit(f"clang compile failed (rc={r.returncode})")
        out = subprocess.run([os.path.join(tmp, "t")], capture_output=True,
                             text=True)
        if out.returncode != 0 or out.stdout.strip() != "357":
            raise AssertionError(f"VK_HEADER_VERSION unexpected: {out.stdout}")
    print("OK: vulkan-headers 1.4.357.0 real API ok (VK_HEADER_VERSION=357)")


if __name__ == "__main__":
    main()
