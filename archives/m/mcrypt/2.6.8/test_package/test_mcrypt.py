#!/usr/bin/env python3
import subprocess
import sys
import tempfile
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: test_mcrypt.py <mcrypt-executable>", file=sys.stderr)
        return 2

    exe = sys.argv[1]
    result = subprocess.run(
        [exe, "--version"],
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
    )
    output = result.stdout.strip()
    if result.returncode != 0:
        print(output)
        print(f"mcrypt --version failed with rc={result.returncode}", file=sys.stderr)
        return 1
    if "mcrypt" not in output.lower() or "2.6.8" not in output:
        print(output)
        print("unexpected mcrypt version output", file=sys.stderr)
        return 1

    plaintext = b"OHOS mcrypt 2.6.8 stdin/stdout roundtrip\n"
    encrypt = subprocess.run(
        [exe, "-q", "-k", "ohos-test-key"],
        check=False,
        input=plaintext,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if encrypt.returncode != 0 or not encrypt.stdout:
        print(encrypt.stderr.decode(errors="replace"))
        print(f"mcrypt encrypt failed with rc={encrypt.returncode}", file=sys.stderr)
        return 1

    decrypt = subprocess.run(
        [exe, "-q", "-d", "-k", "ohos-test-key"],
        check=False,
        input=encrypt.stdout,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )
    if decrypt.returncode != 0:
        print(decrypt.stderr.decode(errors="replace"))
        print(f"mcrypt decrypt failed with rc={decrypt.returncode}", file=sys.stderr)
        return 1
    if decrypt.stdout != plaintext:
        print("mcrypt roundtrip content mismatch", file=sys.stderr)
        return 1

    print(output.splitlines()[0] if output else "mcrypt 2.6.8")
    print("mcrypt stdin/stdout roundtrip ok")

    file_plaintext = b"OHOS mcrypt 2.6.8 file path roundtrip\n"
    with tempfile.TemporaryDirectory(prefix="mcrypt-file-mode-") as tmp:
        work = Path(tmp)
        plain = work / "plain.txt"
        encrypted = work / "plain.txt.nc"
        plain.write_bytes(file_plaintext)

        encrypt = subprocess.run(
            [exe, str(plain), "-q", "-k", "ohos-test-key"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if encrypt.returncode != 0:
            print(encrypt.stderr.decode(errors="replace"))
            print(f"mcrypt file encrypt failed with rc={encrypt.returncode}", file=sys.stderr)
            return 1
        if not encrypted.is_file():
            print("mcrypt file encrypt did not create .nc output", file=sys.stderr)
            return 1

        plain.unlink()
        decrypt = subprocess.run(
            [exe, str(encrypted), "-q", "-d", "-k", "ohos-test-key"],
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
        )
        if decrypt.returncode != 0:
            print(decrypt.stderr.decode(errors="replace"))
            print(f"mcrypt file decrypt failed with rc={decrypt.returncode}", file=sys.stderr)
            return 1
        if plain.read_bytes() != file_plaintext:
            print("mcrypt file roundtrip content mismatch", file=sys.stderr)
            return 1

    print("mcrypt file path roundtrip ok")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
