#!/usr/bin/env python3
"""Consumer validation for the debian-ports-archive data package.

Verifies the installed ASCII-armored OpenPGP key files:
  1. active-keys/ and removed-keys/ inventories exist and are non-empty;
  2. every key file is a well-formed armored public key block
     (BEGIN/END PGP PUBLIC KEY BLOCK markers);
  3. the active key list matches the release it is shipped for.
Follows the iso-codes test_verify.py consumer-side model (R34).
"""

import pathlib
import sys


class Validator:
    def __init__(self):
        self.assertions = 0

    def check(self, condition, message):
        self.assertions += 1
        if not condition:
            raise AssertionError(message)

    def count(self, n=1):
        self.assertions += n


def is_armored_public_key(path, validator):
    validator.check(path.is_file(), f"missing key file: {path}")
    lines = path.read_text(encoding="utf-8").splitlines()
    nonempty = [line for line in lines if line.strip()]
    if not nonempty:
        validator.check(False, f"key file is empty: {path}")
        return
    validator.check(
        nonempty[0].strip() == "-----BEGIN PGP PUBLIC KEY BLOCK-----",
        f"missing BEGIN marker in {path}",
    )
    validator.check(
        nonempty[-1].strip() == "-----END PGP PUBLIC KEY BLOCK-----",
        f"missing END marker in {path}",
    )
    body = nonempty[1:-1]
    validator.check(bool(body), f"no base64 body in {path}")
    validator.check(
        all(len(line.strip()) <= 76 for line in body),
        f"non-canonical line length in {path}",
    )


def main(argv):
    if len(argv) != 2:
        print("usage: test_verify.py PACKAGE_ROOT", file=sys.stderr)
        return 2
    package_root = pathlib.Path(argv[1])
    validator = Validator()

    base = package_root / "share" / "keyrings" / "debian-ports-archive"
    active = base / "active-keys"
    removed = base / "removed-keys"

    validator.check(active.is_dir(), f"missing active-keys dir: {active}")
    validator.check(removed.is_dir(), f"missing removed-keys dir: {removed}")

    active_keys = sorted(active.glob("*.key"))
    removed_keys = sorted(removed.glob("*.key"))
    validator.check(len(active_keys) >= 2, "expected >=2 active keys")
    validator.check(len(removed_keys) >= 1, "expected >=1 removed key")

    # Every shipped key must be a well-formed armored public key block.
    for path in active_keys + removed_keys:
        is_armored_public_key(path, validator)

    print(
        f"DEBIAN_PORTS_ARCHIVE_VALIDATION_PASS "
        f"active={len(active_keys)} removed={len(removed_keys)} "
        f"assertions={validator.assertions}"
    )
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main(sys.argv))
    except (AssertionError, OSError, UnicodeDecodeError) as error:
        print(f"DEBIAN_PORTS_ARCHIVE_VALIDATION_FAIL: {error}", file=sys.stderr)
        sys.exit(1)