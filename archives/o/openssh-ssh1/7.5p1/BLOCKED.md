# openssh-ssh1 7.5p1 validation notes

## Current status

The recipe builds on OHOS armv8 (clang 15, armv8, `conan create` exit 0).
The Conan `test_package` cannot run the three SSH1 functional assertions on
this CI device because OHOS SELinux exposes no writable+executable partition
to the CI account (see blocker B below). On OHOS the `test_package` falls
back to compile-time assertions over the packaged artifacts (each binary
exists, is an ELF, and carries the executable bit). The runtime smoke still
runs on Linux and on OHOS devices that do expose a writable+executable
partition via the script's OHOS guard.
This is a known platform constraint until OHOS SELinux policy evolves to
provide a writable-and-executable staging area.

## Resolved blockers

1. OpenSSH 7.5p1 `config.sub` does not recognize OHOS triplets.
   - Fixed with `0001-config.sub-ohos.patch` and explicit
     `--build=aarch64-linux-ohos` / `--host=aarch64-linux-ohos` configure
     arguments for OHOS.
2. OpenSSH 7.5p1 directly dereferences OpenSSL RSA/DSA/DH internals.
   - OpenSSL 1.1.0 and later, including 1.1.1w, make those structures opaque.
   - Fixed with `0003-openssl-1.1-accessors.patch`.
3. OHOS provides `<shadow.h>` but no usable `getspnam` declaration/symbol.
   - Fixed by forcing `ac_cv_header_shadow_h=no` and by adding
     `0004-xcrypt-guard-getspnam.patch`.
4. Upstream `test_sshkey.c` passes the `banana` function pointer to `memcpy`
   instead of the `the_banana` byte array.
   - Fixed with `0005-test_sshkey-banana-typo.patch`.
5. OpenSSH 7.5p1 Makefile links final executables with `LD` directly.
   - On OHOS this selected `old.lld`, which cannot consume clang-driver flags.
   - Fixed by overriding `LD`/`CCLD` to the configured clang driver and removing
     the unsupported `-lcrypt` link from OHOS make arguments.
6. Conan cache files on OHOS are labeled `u:object_r:hmdfs:s0`, and SELinux
   denies direct ELF execution from that label.
   - Surveyed every writable area exposed to the CI account (`$HOME`,
     conan cache, `/dev/shm`, `$TMPDIR`, `$XDG_CACHE_HOME`): all carry labels
     that forbid execution (`hmdfs`, `dev_shm`, `rootfs`, `hishell_hap_data_file`).
   - The executable area (`u:object_r:hnp_file:s0`, `/data/service/hnp/bin`,
     `$HNP_PUBLIC_HOME`) is read-only for the CI account; `HNP_PRIVATE_HOME`
     (`/data/app`) is also read-only.
   - `setfattr`/`chcon` cannot relabel hmdfs files to `hnp_file` (Operation
     not permitted).
   - With no writable+executable partition available, the `test_package`
     cannot stage `ssh`/`ssh-keygen` for execution on this CI device. On OHOS
     it falls back to compile-time assertions over the packaged artifacts
     (file exists, ELF magic, executable bit). The runtime smoke still runs
     on Linux and on OHOS devices that expose a writable+executable partition.
   - This fallback is the documented behavior for the known platform
     constraint until OHOS SELinux policy evolves.

## Test coverage

- Upstream tests: 14 OpenSSH regression targets are documented in
  `regress/Makefile`.
- Conan `test_package`: 3 functional assertions:
  1. `ssh -V` reports `OpenSSH_7.5p1`.
  2. `ssh -1 -G localhost` accepts SSH protocol 1 mode.
  3. `ssh-keygen -t rsa1` creates non-empty private and public RSA1 key files.
