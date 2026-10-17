# aespipe 2.4h adaptation notes

- Upstream source: `aespipe-v2.4h.tar.bz2`
- Build system: Autotools
- Portability choice: use the upstream portable C implementation by disabling architecture-specific assembly, PadLock, and Intel AES paths.
- Upstream test inventory: 24 groups in the upstream `make tests` target.
- Runtime coverage: deterministic AES-256 encryption/decryption roundtrip, ciphertext inequality, wrong-key negative test, and invalid-option negative test.

Final pass counts and current commit evidence are recorded in the PR after all validation gates complete.
