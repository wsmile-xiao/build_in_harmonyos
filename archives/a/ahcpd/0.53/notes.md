# ahcpd 0.53 Adaptation Notes

## Environment

- Build system: plain Makefile
- Build date: 2026-08-06
- Compiler: clang from the OHOS Conan profile
- Status: built

## Source and Version

- Official source: https://www.irif.fr/~jch/software/files/ahcpd-0.53.tar.gz
- SHA-256: a4622e817d2b2a9b878653f085585bd57f3838cc546cca6028d3b73ffcac0d52
- Upstream tag: ahcpd-0.53
- Upstream release note: CHANGES starts with "8 December 2011: ahcpd 0.53".

## Build

The upstream Makefile builds the daemon directly:

```bash
make -j1
make install TARGET=<package_folder> PREFIX=/usr/local
```

The Makefile respects `CC`, `CFLAGS`, `LDFLAGS`, `TARGET`, and `PREFIX`, so the
Conan recipe can use the generated `conanbuild` environment without patching
upstream sources.

Installed files:

- `usr/local/bin/ahcpd`
- `etc/ahcp/ahcp-config.sh`
- `usr/local/man/man8/ahcpd.8`
- `licenses/LICENCE`

## Dependencies

No third-party Conan dependencies are required. The build links only against
the platform C/POSIX networking interfaces and `-lrt` from the target system.

## Upstream Tests

The official tarball contains no `test` or `check` directory, no test files,
and no `make check` target. Upstream tests are therefore recorded as `0/0`.

## Added Test

The `test_package` contains one consumer smoke test:

```bash
bash test_ahcpd.sh <package>/usr/local/bin/ahcpd
```

It runs `ahcpd` without interface arguments and verifies that the executable
starts, links successfully, returns the documented usage error code, and prints
the usage diagnostic.

The test launcher keeps the OHOS target path `/data/service/hnp/bin/bash` and
falls back to `CONFIG_SHELL` or the host `bash` path for non-OHOS profiles.

## Patches

No patches are applied.

## W3 Device Validation

Device: `currentUser@10.62.148.108:2222`

Input snapshot:

- Local CI input tar: `E:\HarmonyPC\artifacts\ahcpd-0.53-w3-ci-input-r4.tar`
- CI input tar SHA-256: `7c1f2ca2166bade8c3729f9f7145c39d7ad25a24ba73d0e23da0a35fe199a805`
- Remote root: `/storage/Users/currentUser/tmp/ahcpd-slot3-w3-20260806-5`
- Fresh Conan home: `/storage/Users/currentUser/tmp/ahcpd-slot3-w3-20260806-5/conan-home-fresh-1`

Conan validation:

- Command: `CONAN_HOME=<fresh> conan create archives/a/ahcpd/0.53 -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64 -r=ohpcd`
- Recipe revision: `c6cf73adb2beff716d20e94dba4ffe49`
- Package ID: `6b129b068851896169fae42d399fa922d239ce8a`
- Package revision: `ed13f42dc41da670f65dc4ea0187d262`
- Conan log SHA-256: `e76e3813a2a2856821d12b651c8158d56cb459dc4dccac3001049863d889922c`

Results:

- Build: passed with 5 upstream `configure.c` warnings.
- Upstream tests: `0/0` because the official tarball has no test or check target.
- Added tests: `1/1`; `test_package` ran `test_ahcpd.sh` and printed `ahcpd usage smoke test: PASS`.
- Package files include `usr/local/bin/ahcpd`, `etc/ahcp/ahcp-config.sh`, `usr/local/man/man8/ahcpd.8`, and `licenses/LICENCE`.
- Direct package smoke: running packaged `usr/local/bin/ahcpd` without interfaces returned `1` and printed `Syntax: ahcpd` plus `interface`.

Local `ohc-run.py finish` was not used as completion evidence because its local
Windows path invokes unavailable zsh/CI pieces and the bundled local verifier
contains a forbidden `--build=missing` argument. `.ci-result.json` is ignored by
the repository and was not manually created. The authoritative W3 evidence above
is the single-device OHOS Conan run from the frozen input snapshot.
