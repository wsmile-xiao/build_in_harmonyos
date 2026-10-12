#!/usr/bin/env python3
"""pyelftools consumer test (R34): module importable from package
site-packages + real ELFFile API usage (parse hand-crafted minimal
ELF64 aarch64 header, assert machine/type/class fields)."""
import glob
import os
import subprocess
import sys

SMOKE_PY = r'''
import io, os, struct, sys
sys.path[0:0] = os.environ.get("PYTHONPATH", "").split(":")
import elftools
print("pyelftools", elftools.__version__)
assert elftools.__version__ == "0.33", elftools.__version__

from elftools.elf.elffile import ELFFile

# 手工构造最小 ELF64 LE 头 (EM_AARCH64=0xB7, ET_DYN=3, EV_CURRENT=1)
ehdr = struct.pack("<16sHHIQQQIHHHHHH",
    b"\x7fELF\x02\x01\x01\x00" + b"\x00" * 8,
    3, 0xB7, 1, 0, 0, 0, 0, 64, 0, 0, 0, 0, 0)
f = ELFFile(io.BytesIO(ehdr))
assert f.elfclass == 64, f.elfclass
assert f.header.e_machine == "EM_AARCH64", f.header.e_machine
assert f.header.e_type == "ET_DYN", f.header.e_type
print("OK: pyelftools ELFFile parses minimal ELF64 aarch64 header")
'''


def main() -> int:
    if len(sys.argv) < 2:
        print("FAIL: missing package path argument", file=sys.stderr)
        return 1
    pkg = sys.argv[1]
    # 定位包内 site-packages（lib/pythonX.Y/site-packages，兼容版本漂移）
    cands = sorted(glob.glob(os.path.join(pkg, "lib", "python*",
                                          "site-packages")))
    if not cands:
        print(f"FAIL: no site-packages under {pkg}", file=sys.stderr)
        return 1
    site = cands[0]
    mod = os.path.join(site, "elftools", "__init__.py")
    if not os.path.isfile(mod):
        print(f"FAIL: elftools module missing: {mod}", file=sys.stderr)
        return 1
    env = dict(os.environ)
    env["PYTHONPATH"] = site
    # 用调用本脚本的 python（必然存在且可执行——沙箱 PATH 无 python3 实测）
    py = sys.executable
    r = subprocess.run([py, "-c", SMOKE_PY], capture_output=True,
                       text=True, env=env)
    if r.returncode != 0:
        print(f"FAIL: pyelftools API: {r.stderr}", file=sys.stderr)
        return 1
    print(r.stdout.strip())
    print("OK: pyelftools module + ELFFile real API works")
    return 0


if __name__ == "__main__":
    sys.exit(main())
