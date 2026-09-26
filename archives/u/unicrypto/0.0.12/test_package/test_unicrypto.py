#!/usr/bin/env python3
"""unicrypto consumer smoke test (R34): standalone test source executed via
self.run from test_package/conanfile.py test().

R34: actually call the tested API. unicrypto exposes a unified interface over
AES/DES/TDES/RC4 ciphers plus hash/PBKDF2/HMAC/CMAC/KDF. On HarmonyOS only the
self-contained pure-Python backend is guaranteed available (the C-accelerated
backend pycryptodomex etc. are not published for OHOS), so we exercise the
`pure` backend against well-known NIST / RFC 6070 vectors and assert results.

At the end emits the HMBS test-package marker with the real assertion count.

Usage: test_unicrypto.py <site-packages>
Returns non-zero on any assertion failure.
"""
import json
import os
import sys


def main() -> int:
    if len(sys.argv) != 2:
        print(f"usage: {sys.argv[0]} <site-packages>", file=sys.stderr)
        return 2
    site = sys.argv[1]
    if not os.path.isdir(os.path.join(site, "unicrypto")):
        raise AssertionError(f"unicrypto package missing in {site!r}")
    sys.path = [site] + sys.path

    from unicrypto import get_cipher_by_name, hashlib
    from unicrypto import symmetric
    from unicrypto.pbkdf2 import pbkdf2

    passed = 0

    def check(cond, msg):
        nonlocal passed
        if not cond:
            raise AssertionError(msg)
        passed += 1

    # 1) AES-128-ECB — NIST FIPS-197 / Crypto++ aes.txt vector (pure backend)
    AES = get_cipher_by_name("AES", "pure")
    key = bytes.fromhex("2b7e151628aed2a6abf7158809cf4f3c")
    pt = bytes.fromhex("6bc1bee22e409f96e93d7e117393172a")
    expected_ct = bytes.fromhex("3ad77bb40d7a3660a89ecaf32466ef97")
    enc = AES(key, symmetric.MODE_ECB).encrypt(pt)
    check(enc == expected_ct, f"AES-ECB mismatch: {enc.hex()!r}")
    check(AES(key, symmetric.MODE_ECB).decrypt(enc) == pt,
          "AES-ECB roundtrip failed")

    # 2) DES-ECB — vector (pure backend)
    DES = get_cipher_by_name("DES", "pure")
    des_enc = DES(bytes.fromhex("0000000000000000"),
                  symmetric.MODE_ECB).encrypt(bytes.fromhex("0000000000000000"))
    check(des_enc.hex().upper() == "8CA64DE9C1B123A7",
          f"DES-ECB mismatch: {des_enc.hex()!r}")

    # 3) PBKDF2-HMAC-SHA1 — RFC 6070 vectors (pure hashlib)
    sha1 = hashlib.sha1
    v1 = pbkdf2(b"password", b"salt", 1, 20, digestmod=sha1)
    v2 = pbkdf2(b"password", b"salt", 2, 20, digestmod=sha1)
    check(v1.hex() == "0c60c80f961f0e71f3a9b524af6012062fe037a6",
          f"PBKDF2 v1 mismatch: {v1.hex()!r}")
    check(v2.hex() == "ea6c014dc72d6f8ccd1ed92ace1d41f0d8de8957",
          f"PBKDF2 v2 mismatch: {v2.hex()!r}")

    # 4) SHA1 — known FIPS digest
    h = hashlib.sha1()
    h.update(b"abc")
    check(h.digest().hex() == "a9993e364706816aba3e25717850c26c9cd0d89d",
          f"SHA1 mismatch: {h.digest().hex()!r}")

    print(f"OK: unicrypto 0.0.12 (pure backend AES/DES/PBKDF2/SHA1: "
          f"{passed}/{passed})")
    print("HMBS_TEST_PACKAGE_RESULT=" + json.dumps({
        "executed": True,
        "passed": True,
        "command": "python3 test_unicrypto.py <site-packages>",
        "discovered": passed,
        "passedCount": passed,
    }))
    return 0


if __name__ == "__main__":
    sys.exit(main())
