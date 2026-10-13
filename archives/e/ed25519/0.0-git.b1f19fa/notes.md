# ed25519 0.0-git.b1f19fa OHOS PC 适配笔记

## Upstream

- Repository: https://github.com/orlp/ed25519
- Fixed commit: `b1f19fab4aebe607805620d25a5e42566ce46a0e` (master HEAD, verified via git ls-remote)
- License: Zlib (license.txt, Orson Peters, 2015)
- Language: C99
- Third-party dependencies: none — SHA-512, field/group/scalar arithmetic all in-tree

Upstream publishes no release or version tag. The package version
`0.0-git.b1f19fa` follows the git-snapshot convention: `0.0` because the
project never declared a version, `git` + abbreviated commit hash for
reproducibility.

## Build

Upstream ships NO build system at all — no CMakeLists.txt, no Makefile.
The integration model documented in the readme is "add all .c and .h
files in the src/ folder to your project". The recipe therefore compiles
the ten upstream src/*.c translation units directly with the HarmonyOS
Clang toolchain (`-std=c99 -Wall -pedantic -O2`, compiler resolved from
`tools.build:compiler_executables` conf, R33), archives `libed25519.a`
with llvm-ar, and packages the library plus headers and license. No
source patch is required. The two prebuilt Windows DLLs in the tarball
root (ed25519_32.dll / ed25519_64.dll) are never packaged.

## API 形态（与 RFC 8032 语义的差异点）

- `private_key` is NOT the 32-byte seed: `ed25519_create_keypair`
  outputs a 64-byte buffer (expanded seed || public key) which is what
  `ed25519_sign` / `ed25519_key_exchange` consume.
- Signatures are deterministic (RFC 8032), so the official RFC vectors
  can be reproduced byte-for-byte from the seed alone.

## Upstream tests

Upstream ships one driver, test.c, that exercises the whole API:
keypair + sign + verify on a random seed, re-sign + verify after
`ed25519_add_scalar`, tampered-signature rejection (`signature[44] ^=
0x10` must NOT verify), key-exchange agreement from both sides, and six
10000-iteration performance sweeps. The driver always exits 0, so the
recipe asserts on stdout instead: the four semantic checks must print
their happy-path lines ("valid signature" exactly twice, "correctly
detected signature change", "key exchange was correct") and no
failure-path line may appear. Counted as one upstream test boundary with
4 runtime assertions; the timing sweeps are performance output only and
are not counted.

## Consumer test

One Conan consumer executable links the packaged `ed25519::ed25519`
target and runs the official RFC 8032 section 7.1 Ed25519 test vectors
(TEST 1 empty message / TEST 2 one byte / TEST 3 two bytes): 3 vectors
x 4 assertions = 12 assertions (expected public key derivation, exact
deterministic signature match, verify accept, verify reject on a
tampered signature byte).

## 验证结果

```bash
$ conan create . -pr:h=ohos-aarch64 --build=missing
...
ed25519/0.0-git.b1f19fa: Package '...' built
...
ok: keypair derives the RFC 8032 public key      # x3 vectors
ok: sign produces the deterministic RFC 8032 signature
ok: verify accepts the RFC 8032 signature
ok: verify rejects a tampered signature
ed25519 consumer test passed: 12 assertions
```
