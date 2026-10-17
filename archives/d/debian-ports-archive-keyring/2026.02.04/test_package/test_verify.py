#!/usr/bin/env python3
"""Verify the packaged debian-ports-archive-keyring data (no gpg/network)."""
import base64
import hashlib
import os
import re
import sys


EXPECTED_SHA = {
    "debian-ports-archive-2026.asc":
        "e7c5cd21987bac198e1536d12a2d7cfadbf0979e063d07838165df25dc4de7d0",
    "debian-ports-archive-2027.asc":
        "d91ed90ad85d43447da9af784e3fbd0fd4c447aa3596d0667a1ad6354ba13a82",
    "debian-ports-archive-keyring.pgp":
        "7d5da83561d53da68cc44141fc34fba1c174ce073f379576091a8d9ea21bf793",
    "debian-ports-archive-keyring-removed.pgp":
        "383db113d9f362efc25bfdd11b630c7b39695f329f3be11dd874c264fc4206be",
}
# Active key fingerprints (gpg --show-keys 与纯 python v4 计算一致, 2026-09-09)
ACTIVE_FPS = {
    "5FFACC4B97F15BF3636639EBC6894E6BB25B9C99",  # 2026 (expires 2027-02-01)
    "16AD6A4476B489F604203E42C5934E9A2B1BE090",  # 2027 (expires 2028-02-01)
}
EXPECTED_ACTIVE_KEYS = 2
EXPECTED_REMOVED_KEYS = 19


def armor_payload(data: bytes) -> bytes:
    text = data.decode("utf-8", errors="replace")
    m = re.search(r"-----BEGIN [^-]+-----\n(.*?)-----END [^-]+-----", text, re.S)
    if not m:
        raise AssertionError("not an OpenPGP armor block")
    lines = m.group(1).split("\n")
    i = 0
    while i < len(lines) and lines[i].strip() != "":
        i += 1
    body = [l.strip() for l in lines[i:] if l.strip() and not l.startswith("=")]
    return base64.b64decode("".join(body), validate=True)


def primary_key_count_and_fps(data: bytes):
    """Scan OpenPGP packets; return (n_primary_pubkeys, [v4 fingerprints])."""
    fps = []
    n = 0
    i = 0
    while i < len(data):
        b = data[i]
        new = not (b & 0x80)
        tag = (b >> 2) & (0x0f if new else 0x1f)
        lt = b & 3
        i += 1
        if lt == 0:
            ln = data[i]; i += 1
        elif lt == 1:
            ln = int.from_bytes(data[i:i + 2], "big"); i += 2
        elif lt == 2:
            ln = int.from_bytes(data[i:i + 4], "big"); i += 4
        else:
            ln = len(data) - i  # indeterminate/partial: consume remainder (rare)
        body = data[i:i + ln]
        i += ln
        if tag == 6:
            n += 1
            if body and body[0] == 4:  # v4 fingerprint
                fps.append(
                    hashlib.sha1(b"\x99" + len(body).to_bytes(2, "big") + body)
                    .hexdigest().upper())
    return n, fps


def main():
    keydir = sys.argv[1]
    if not os.path.isdir(keydir):
        print(f"FAIL: keyrings dir missing: {keydir}")
        return 1
    files = sorted(os.listdir(keydir))
    expected_files = set(EXPECTED_SHA)
    if set(files) != expected_files:
        print(f"FAIL: file set {files} != expected {sorted(expected_files)}")
        return 1

    for name in sorted(expected_files):
        path = os.path.join(keydir, name)
        with open(path, "rb") as fh:
            blob = fh.read()
        if hashlib.sha256(blob).hexdigest() != EXPECTED_SHA[name]:
            print(f"FAIL: {name} sha256 != official deb 值")
            return 1

    # active binary keyring: exactly 2 primary keys, known fingerprints
    with open(os.path.join(keydir, "debian-ports-archive-keyring.pgp"), "rb") as fh:
        act = fh.read()
    n_act, fps_act = primary_key_count_and_fps(act)
    if n_act != EXPECTED_ACTIVE_KEYS or set(fps_act) != ACTIVE_FPS:
        print(f"FAIL: active keyring keys={n_act} fps={fps_act} "
              f"(expect {EXPECTED_ACTIVE_KEYS} {sorted(ACTIVE_FPS)})")
        return 1

    # .asc == armored active keys, decodable to the same two fingerprints
    for y in ("2026", "2027"):
        with open(os.path.join(keydir, f"debian-ports-archive-{y}.asc"), "rb") as fh:
            payload = armor_payload(fh.read())
        _, fps_asc = primary_key_count_and_fps(payload)
        if not fps_asc or fps_asc[0] not in ACTIVE_FPS:
            print(f"FAIL: {y}.asc decode failed {fps_asc}")
            return 1

    # removed binary keyring: exactly 19 primary keys (2007-2025)
    with open(os.path.join(keydir,
                           "debian-ports-archive-keyring-removed.pgp"), "rb") as fh:
        rem = fh.read()
    n_rem, _ = primary_key_count_and_fps(rem)
    if n_rem != EXPECTED_REMOVED_KEYS:
        print(f"FAIL: removed keyring primary keys={n_rem} != {EXPECTED_REMOVED_KEYS}")
        return 1

    print(f"OK: keyrings verified (files={len(files)}, active={n_act}, "
          f"removed={n_rem}, all sha256 == official Debian .deb)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
