#!/usr/bin/env python3
"""Conan consumer test for wagyu 0.6.1 (Rust binary package).

Two layers of assertions (each printed on its own line so the counts quoted
in the PR description stay auditable):

  A. Consumer smoke + functional tests — run the packaged `wagyu` binary:
     help output, and *real wallet generation* over two chains plus a
     non-default network. Wallet generation exercises the full entropy path
     (rand 0.7 → getrandom 0.1 → getrandom(2) syscall) that the recipe's
     registry patch re-enables on OHOS — a static binary check would not
     prove it.

  B. HarmonyOS-specific (鸿蒙特有) assertions — verify the platform traits
     that make the artifact usable on OHOS at all:
       B1. ELF machine is AArch64 (the OHOS PC target)
       B2. PT_INTERP is the OHOS musl loader (ld-musl-aarch64.so.1)
       B3. the binary carries an OHOS code signature (HarmonyOS refuses
           execve of unsigned ELF — errno 13)
       B4. non-empty regular executable file
"""

import json
import os
import struct
import subprocess
import sys

PASSED = 0
FAILED = 0

OHOS_MUSL_LOADER = "ld-musl-aarch64.so.1"
EM_AARCH64 = 183


def check(name, ok, detail=""):
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"[ok] {name}{(': ' + detail) if detail else ''}")
    else:
        FAILED += 1
        print(f"[fail] {name}{(': ' + detail) if detail else ''}", file=sys.stderr)
    return ok


def elfinfo(path):
    """Return (e_machine, interp) or (None, None) when unreadable."""
    try:
        with open(path, "rb") as fh:
            data = fh.read()
    except OSError:
        return None, None
    if data[:4] != b"\x7fELF":
        return None, None
    e_machine = struct.unpack_from("<H", data, 18)[0]
    phoff = struct.unpack_from("<Q", data, 0x20)[0]
    phentsize = struct.unpack_from("<H", data, 0x36)[0]
    phnum = struct.unpack_from("<H", data, 0x38)[0]
    interp = None
    for i in range(phnum):
        off = phoff + i * phentsize
        if struct.unpack_from("<I", data, off)[0] == 3:  # PT_INTERP
            p_offset = struct.unpack_from("<Q", data, off + 8)[0]
            p_filesz = struct.unpack_from("<Q", data, off + 32)[0]
            interp = (data[p_offset:p_offset + p_filesz]
                      .rstrip(b"\x00").decode("utf-8", "replace"))
            break
    return e_machine, interp


def run(exe, args, timeout=120):
    return subprocess.run([exe] + args, capture_output=True, text=True,
                          timeout=timeout)


def main():
    package_folder = os.environ.get("PACKAGE_FOLDER", "")
    exe = os.path.join(package_folder, "bin", "wagyu")

    # ── B. 鸿蒙特有测试 (HarmonyOS-specific) ──
    print("== 鸿蒙特有测试 / HarmonyOS-specific assertions ==")
    size = os.path.getsize(exe) if os.path.isfile(exe) else 0
    if not check("B4: wagyu is a non-empty regular executable file",
                 os.path.isfile(exe) and size > 0, f"{size} bytes"):
        raise AssertionError(f"Missing wagyu executable: {exe}")

    with open(exe, "rb") as fh:
        payload = fh.read()
    e_machine, interp = elfinfo(exe)
    check("B1: ELF machine is AArch64 (EM_AARCH64=183)",
          e_machine == EM_AARCH64, f"e_machine={e_machine}")
    check(f"B2: PT_INTERP is the OHOS musl loader ({OHOS_MUSL_LOADER})",
          interp is not None and OHOS_MUSL_LOADER in interp, f"interp={interp}")
    check("B3: OHOS code signature present (unsigned ELF cannot execve)",
          b"codesign" in payload)

    # ── A. 消费者冒烟 + 功能测试 ──
    print("== 消费者冒烟测试 / consumer smoke & functional tests ==")

    help_run = run(exe, ["--help"], timeout=60)
    if not check("A1: `wagyu --help` exits 0 and self-reports v0.6.1",
                 help_run.returncode == 0 and "wagyu v0.6.1" in help_run.stdout,
                 f"rc={help_run.returncode} head="
                 f"{help_run.stdout.splitlines()[0] if help_run.stdout else ''}"):
        raise AssertionError("`wagyu --help` version self-check failed")
    check("A2: help lists the bitcoin subcommand",
          "bitcoin" in help_run.stdout and "Generate a wallet"
          in help_run.stdout)

    btc_help = run(exe, ["bitcoin", "--help"], timeout=60)
    check("A3: `wagyu bitcoin --help` exits 0 and documents --count/--json",
          btc_help.returncode == 0 and "--count" in btc_help.stdout
          and "--json" in btc_help.stdout, f"rc={btc_help.returncode}")

    gen = run(exe, ["bitcoin", "--count", "2", "--json"], timeout=120)
    if not check("A4: `wagyu bitcoin --count 2 --json` exits 0",
                 gen.returncode == 0,
                 f"rc={gen.returncode} err={gen.stderr.strip()[:160]}"):
        raise AssertionError("wallet generation failed")
    wallets = None
    try:
        wallets = json.loads(gen.stdout)
    except ValueError:
        pass
    if not check("A5: generation output parses as a JSON array of 2 wallets",
                 isinstance(wallets, list) and len(wallets) == 2,
                 f"items={len(wallets) if isinstance(wallets, list) else 'n/a'}"):
        raise AssertionError("bad JSON output")
    # A6：默认输出 compressed:true → bitcoin 公钥是 33 字节压缩形态（66 hex）；
    # 未压缩形态 130 hex 也接受。任一字段不合法时把具体原因带进 detail，便于归因。
    def _btc_wallet_problem(w):
        if not isinstance(w, dict):
            return "entry not an object"
        pk, pub, addr = w.get("private_key"), w.get("public_key"), w.get("address")
        if not isinstance(pk, str) or not 51 <= len(pk) <= 52:
            return "private_key not 51-52 chars: %r" % (
                len(pk) if isinstance(pk, str) else pk)
        if not isinstance(pub, str) or len(pub) not in (66, 130):
            return "public_key not 66/130 hex chars: %r" % (
                len(pub) if isinstance(pub, str) else pub)
        if not isinstance(addr, str) or len(addr) < 26:
            return "address too short: %r" % (
                len(addr) if isinstance(addr, str) else addr)
        if w.get("network") != "mainnet":
            return "network=%r" % (w.get("network"),)
        if w.get("format") != "p2pkh":
            return "format=%r" % (w.get("format"),)
        return None

    problems = [p for p in (_btc_wallet_problem(w) for w in wallets) if p]
    addresses = [w.get("address") for w in wallets if isinstance(w, dict)]
    dup = len(set(addresses)) != len(addresses)
    check("A6: WIF private key / secp256k1 public key / P2PKH address fields valid",
          not problems and not dup,
          "; ".join(problems) if problems else
          ("duplicate addresses" if dup else "2 unique mainnet p2pkh wallets"))

    eth = run(exe, ["ethereum", "--count", "1", "--json"], timeout=120)
    eth_wallets = None
    try:
        eth_wallets = json.loads(eth.stdout)
    except ValueError:
        pass
    check("A7: `wagyu ethereum --count 1 --json` exits 0 with a wallet",
          eth.returncode == 0 and isinstance(eth_wallets, list)
          and len(eth_wallets) == 1
          and str(eth_wallets[0].get("address", "")).startswith("0x"),
          f"rc={eth.returncode}")

    tnet = run(exe, ["bitcoin", "--network", "testnet", "--count", "1",
                     "--json"], timeout=120)
    tnet_wallets = None
    try:
        tnet_wallets = json.loads(tnet.stdout)
    except ValueError:
        pass
    check("A8: `wagyu bitcoin --network testnet --count 1 --json` exits 0",
          tnet.returncode == 0 and isinstance(tnet_wallets, list)
          and len(tnet_wallets) == 1
          and tnet_wallets[0].get("network") == "testnet",
          f"rc={tnet.returncode}")

    print(f"SUMMARY: executed={PASSED + FAILED} passed={PASSED} "
          f"failed={FAILED} (harmonyos_specific=4)")
    if FAILED:
        raise AssertionError(f"{FAILED} assertion(s) failed")
    print("wagyu test_package OK: HarmonyOS traits + wallet generation verified")


if __name__ == "__main__":
    sys.exit(main())
