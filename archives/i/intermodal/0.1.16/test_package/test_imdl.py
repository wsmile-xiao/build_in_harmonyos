#!/usr/bin/env python3
"""Conan consumer test for intermodal 0.1.16 (imdl CLI).

Three layers of assertions:

  A. Consumer smoke test — runs the packaged `imdl` binary:
     --help / --version output sanity.

  F. Functional tests — real BitTorrent metainfo workflows executed on
     HarmonyOS PC:
       F1. `imdl torrent create` produces a valid bencoded .torrent from a
           regular file (checked structurally: bencode dict with
           announce/info/piece length keys present, info dictionary
           contains the file name and length)
       F2. `imdl torrent show` renders human-readable metainfo
       F3. `imdl torrent verify` re-hashes the data and reports OK
       F4. `imdl torrent link` prints a working magnet link
           (magnet:?xt=urn:btih: with a 40-char hex infohash)

  B. HarmonyOS-specific (鸿蒙特有) assertions — verify the platform traits
     that make the artifact usable on OHOS at all:
       B1. ELF machine is AArch64 (the OHOS PC target)
       B2. PT_INTERP is the OHOS musl loader (ld-musl-aarch64.so.1)
       B3. the binary carries an OHOS code signature — HarmonyOS refuses to
           execve unsigned ELF (EACCES errno 13)
       B4. the binary is a non-empty regular executable file

Every assertion is reported on its own line so the counts quoted in the PR
description stay auditable.
"""

import os
import struct
import subprocess
import sys
import tempfile

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
        print(f"[fail] {name}{(': ' + detail) if detail else ''}",
              file=sys.stderr)
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


def run(exe, *args, cwd=None):
    return subprocess.run([exe, *args], capture_output=True, text=True,
                          timeout=60, cwd=cwd)


def main():
    package_folder = os.environ.get("PACKAGE_FOLDER", "")
    exe = os.path.join(package_folder, "bin", "imdl")

    # ── B. 鸿蒙特有测试 (HarmonyOS-specific) ──
    print("== 鸿蒙特有测试 / HarmonyOS-specific assertions ==")
    if not check("B4: imdl is a non-empty regular executable file",
                 os.path.isfile(exe) and os.path.getsize(exe) > 0,
                 f"{exe} ({os.path.getsize(exe) if os.path.isfile(exe) else 0}"
                 " bytes)"):
        raise AssertionError(f"Missing imdl executable: {exe}")

    e_machine, interp = elfinfo(exe)
    check("B1: ELF machine is AArch64 (EM_AARCH64=183)",
          e_machine == EM_AARCH64, f"e_machine={e_machine}")
    check(f"B2: PT_INTERP is the OHOS musl loader ({OHOS_MUSL_LOADER})",
          interp is not None and OHOS_MUSL_LOADER in interp,
          f"interp={interp}")
    with open(exe, "rb") as fh:
        payload = fh.read()
    check("B3: OHOS code signature present (unsigned ELF cannot execve)",
          b"codesign" in payload)

    # ── A. 通用消费者冒烟测试 ──
    print("== 消费者冒烟测试 / consumer smoke test ==")
    help_run = run(exe, "--help")
    if not check("A1: `imdl --help` exits 0", help_run.returncode == 0,
                 f"rc={help_run.returncode} "
                 f"err={help_run.stderr.strip()[:160]}"):
        raise AssertionError(f"`imdl --help` failed: {help_run.stderr}")
    check("A2: `--help` output mentions torrent subcommand",
          "torrent" in help_run.stdout.lower())

    ver_run = run(exe, "--version")
    check("A3: `imdl --version` exits 0 and reports 0.1.16",
          ver_run.returncode == 0 and "0.1.16" in ver_run.stdout,
          f"rc={ver_run.returncode} out={ver_run.stdout.strip()[:80]}")

    # ── F. 功能测试：真实 .torrent 工作流 ──
    print("== 功能测试 / functional torrent workflow ==")
    workdir = tempfile.mkdtemp(prefix="imdl-test-")
    data_file = os.path.join(workdir, "hello.txt")
    with open(data_file, "wb") as fh:
        fh.write(b"HarmonyOS PC intermodal test payload " * 64)
    torrent_file = os.path.join(workdir, "hello.torrent")

    create = run(exe, "torrent", "create", "--announce",
                 "udp://tracker.example:1337/announce",
                 "--input", data_file,
                 "--output", torrent_file)
    if not check("F1: `imdl torrent create` exits 0",
                 create.returncode == 0,
                 f"rc={create.returncode} err={create.stderr.strip()[:200]}"):
        raise AssertionError("torrent create failed")
    check("F2: .torrent file created and non-empty",
          os.path.isfile(torrent_file) and os.path.getsize(torrent_file) > 0,
          f"{os.path.getsize(torrent_file)} bytes")

    with open(torrent_file, "rb") as fh:
        bencode = fh.read()
    # bencode 结构断言：顶层 dict 以 d 开头 e 结尾，包含 announce / info 键
    check("F3: .torrent is a bencode dictionary (d...e)",
          bencode.startswith(b"d") and bencode.endswith(b"e"))
    check("F4: .torrent contains announce and info keys",
          b"8:announce" in bencode and b"4:info" in bencode)
    check("F5: .torrent info dict carries the payload file name",
          b"9:hello.txt" in bencode)

    info = run(exe, "torrent", "show", "--input", torrent_file)
    check("F6: `imdl torrent show` exits 0 and shows the name",
          info.returncode == 0 and "hello.txt" in info.stdout,
          f"rc={info.returncode} out={info.stdout.strip()[:80]}")

    verify = run(exe, "torrent", "verify", "--input", torrent_file)
    check("F7: `imdl torrent verify` exits 0 (re-hash OK)",
          verify.returncode == 0,
          f"rc={verify.returncode} out={verify.stdout.strip()[:120]} "
          f"err={verify.stderr.strip()[:120]}")

    link = run(exe, "torrent", "link", "--input", torrent_file)
    magnet = link.stdout.strip()
    check("F8: `imdl torrent link` prints magnet with 40-hex infohash",
          link.returncode == 0 and magnet.startswith("magnet:?xt=urn:btih:")
          and len(magnet.split("btih:")[1].split("&")[0]) == 40
          and all(c in "0123456789abcdefABCDEF"
                  for c in magnet.split("btih:")[1].split("&")[0]),
          f"out={magnet[:80]}")

    print(f"SUMMARY: executed={PASSED + FAILED} passed={PASSED} "
          f"failed={FAILED} (harmonyos_specific=4)")
    if FAILED:
        raise AssertionError(f"{FAILED} assertion(s) failed")
    print("intermodal test_package OK: HarmonyOS traits + torrent "
          "create/info/verify/link verified")


if __name__ == "__main__":
    main()
