# reop 2.1.1 native test report

Platform: OpenHarmony 6.1.0.115, aarch64, Clang 15, Conan 2.29.1.

## Upstream tests

Command: `sh tests/test.sh` from the patched Conan build tree. Result: `All passed.` (exit 0). The script exercises key generation, authenticated encryption in text and binary modes, decryption round trips, signing, verification, and rejection of a signature with the wrong public key.

## Packaged consumer

Command: `conan create . -s os.version=6.0 -r=ohpcd --build=missing`. Result: exit 0. `test_package/test.sh` used the installed `bin/reop` to generate a keypair, sign and verify a file, encrypt and decrypt it, and compare the recovered file byte for byte.

## Repository verifier

Command: `python3 scripts/ohc-run.py conan-verify reop 2.1.1`. Result: pass; it passed G1 recipe checks, G2 clean Conan build, G3 library isolation, and G4 artifact checks.
