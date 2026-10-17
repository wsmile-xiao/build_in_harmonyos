#!/usr/bin/env python3
"""test_package — bitcoin 消费验证（L0d: test() 必须 self.run）。

验证 bin/bitcoind + bitcoin-cli 存在且为合法 ELF 可执行文件（OHOS headless
无法完整运行 P2P 节点，验证二进制有效 + --version 输出）。
"""
import os
import struct
import subprocess
import sys


def check_elf(path):
    with open(path, "rb") as f:
        magic = f.read(4)
    if magic != b"\x7fELF":
        return False, "not ELF magic"
    with open(path, "rb") as f:
        f.seek(16)
        e_type = struct.unpack("<H", f.read(2))[0]
    kind = {2: "ET_EXEC", 3: "ET_DYN"}.get(e_type, f"ET_{e_type}")
    return True, kind


def main():
    pkg = sys.argv[1] if len(sys.argv) > 1 else os.environ.get("PACKAGE_FOLDER", "")
    bins = os.path.join(pkg, "bin")
    found = []
    for exe in ("bitcoind", "bitcoin-cli"):
        cand = os.path.join(bins, exe)
        if not os.path.isfile(cand):
            print(f"FAIL: missing {cand}")
            return 1
        ok, kind = check_elf(cand)
        if not ok:
            print(f"FAIL: {cand} {kind}")
            return 1
        found.append(f"{exe}({kind})")
    print(f"OK: bitcoind/bitcoin-cli are valid ELF executables: {' '.join(found)}")
    # --version 输出验证（--disable-wallet 构建，bitcoind 应能打印版本；
    # 失败须 FAIL（return 1）而非 WARN——合法 ELF 但无法运行/崩溃必须拦截）
    try:
        r = subprocess.run([os.path.join(bins, "bitcoind"), "--version",
                            "-datadir=."],
                           capture_output=True, text=True, timeout=30)
        out = r.stdout or r.stderr or ""
        if r.returncode != 0:
            print(f"FAIL: bitcoind --version exit {r.returncode}: {(out or '')[:200]}")
            return 1
        if "Bitcoin Core version v27" in out:
            print("OK: bitcoind --version ->", out.strip().splitlines()[0][:50])
        else:
            print(f"FAIL: bitcoind --version unexpected: {(out or '')[:200]}")
            return 1
    except subprocess.TimeoutExpired:
        print("FAIL: bitcoind --version timed out (binary may hang)")
        return 1
    except Exception as e:
        print(f"FAIL: bitcoind --version error: {e}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
