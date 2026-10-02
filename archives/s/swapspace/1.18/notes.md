# swapspace 1.18 adaptation notes

## Status

- Conan reference: `swapspace/1.18`
- Branch: `feat/swapspace-1.18`
- Current stage: W0–W5 completed; aarch64 OHOS cross-compile, Conan
  create/package and the consumer test suite all pass
- Upstream: https://github.com/Tookmund/Swapspace

## W0 dependency check

swapspace 1.18 has no third-party runtime, build, or test dependencies. It
is a single C99 program that links against libc only. `conan search
"swapspace/*" -r=ohpcd` reports no pre-existing recipe, and the recipe
declares no `requires()`/`tool_requires()`, so there is nothing to publish
downstream before building this package.

The only non-POSIX surface it touches is Linux's swap subsystem:

- `swapon(2)` / `swapoff(2)` — declared in `<sys/swap.h>` and present in
  the OHOS runtime libc
- `<linux/fs.h>`, `<linux/magic.h>` — BTRFS/`FICLONE` support (both headers
  present in the OHOS sysroot)
- `/proc/meminfo`, `/proc/swaps` — the standard Linux procfs memory files

No dependency had to be adapted first, so the W0 gate is satisfied without
a separate dependency PR.

## W0b history check

`git ls-tree -r origin/main archives/s/` shows no prior `swapspace`
directory, so there is no historical `notes.md` to reconcile against and
no prior version whose recipe structure this one must stay compatible with.

The CI capability matrix was checked against the build requirements:

| Tool | Needed | CI status | Outcome |
|---|---|---|---|
| clang | yes | available | used via `tools.build:compiler_executables` |
| make / autotools | no | — | deliberately avoided (see below) |
| Rust | no | n/a | n/a |

The upstream tarball ships only `configure.ac`, not a generated
`configure`. Driving it through autotools would therefore require
`autoreconf` in the recipe, adding a `tool_requires` chain (autoconf /
automake / m4 / perl) purely to regenerate a build system for a 7-file
program. The recipe instead reproduces the target/source mapping of
upstream's own hand-written `src/Makefile.static` with direct clang
invocations, which is the same approach the `cronutils` recipe uses for
its raw-Makefile sources. This keeps the package free of host build-tool
dependencies and removes a failure mode rather than adding one.

## Source

- URL: `https://github.com/Tookmund/Swapspace/archive/refs/tags/v1.18.tar.gz`
- SHA256: `4efbf0815c3e3f85e907a693ab5e74ae99f0041a3bb41358c68c2d4ac370fec2`
- Archive format: tar.gz, upstream root `Swapspace-1.18`
- License: GPL-2.0-only (shipped as `COPYING`)
- Tag `v1.18` is the official GitHub release for the 1.18 line (1.18.1 is a
  later maintenance release; this package targets 1.18 as requested)

## HarmonyOS build decisions

1. **No autotools.** See the W0b section. `build()` invokes clang once per
   translation unit and links the seven objects into `swapspace`, mirroring
   `src/Makefile.static`.
2. **Compiler from `tools.build:compiler_executables`.** No bare `${CC}` /
   `${CFLAGS}` in any `self.run()` string (R33), so the recipe behaves the
   same on the CI worker and on a locally overridden profile.
3. **`--std=gnu99`.** swapspace is C99 with one extension: it uses POSIX
   `sigaction()` under `-pedantic`, which strict C99 mode rejects. Upstream's
   own static makefile selects `gnu99` for the same reason.
4. **`config.h` is generated, not patched.** The tarball has no generated
   `config.h`; upstream ships `config.h.static` for its static makefile
   path, which the recipe copies into place. `PACKAGE_NAME`,
   `PACKAGE_VERSION` and `PACKAGE_STRING` are supplied as `-D` flags with
   the values `AC_INIT([swapspace], [1.18], ...)` would have produced, so
   `--version` prints `swapspace 1.18`. `HAVE_SWAPON` / `HAVE_SWAPOFF` come
   from `config.h.static`, which is correct here: the OHOS runtime libc
   exports both symbols, so `src/support.c` does not need its
   `/sbin/swapon` command fallback.
5. **`-DVARPREFIX` / `-DETCPREFIX`** must be the *parent* directories, not
   the final ones. `src/swaps.c` declares the default swap directory as
   `VARPREFIX"/lib/swapspace"` and `src/opts.c` declares the default config
   file as `ETCPREFIX"/swapspace.conf"`. `-DVARPREFIX="/var"` yields
   `/var/lib/swapspace`, matching `Makefile.am`'s
   `$(localstatedir)/lib/swapspace`; `-DETCPREFIX="/etc"` yields
   `/etc/swapspace.conf`, matching `sysconf_DATA` (installed with no
   subdirectory). Passing `/var/lib` here compiles the doubled, wrong
   `/var/lib/lib/swapspace` into the binary. The test package pins this by
   asserting the literal `/var/lib/swapspace` in the daemon's own error
   message, so a wrong prefix fails CI.
6. **Shell quoting for `-D` flags.** `DATE` and `PACKAGE_STRING` contain
   spaces, so each flag is wrapped in shell single quotes. Without this the
   value splits into separate argv words and clang reports
   `no such file or directory: 'Jan'` — the first build failure hit here.
7. **`hog` is built but not packaged.** It is upstream's separate
   memory-hog helper (`noinst_PROGRAMS`) with its own `main()`. It is
   compiled and linked to keep the build faithful to
   `make -f Makefile.static all`, but upstream does not install it, so it
   stays out of the package. It must be a *separate* link step: linking its
   object together with the daemon's objects gives
   `duplicate symbol: main`.
8. **Package layout** follows the upstream install target's file *names*:
   the daemon in `bin/`, the man page in `share/man/man8/`, the sample
   configuration at `etc/swapspace.conf` (the exact path the binary reads),
   and `COPYING` in `licenses/`. Upstream uses `sbin_PROGRAMS`; Conan
   packages expose commands via `bindirs`, so the daemon lands in `bin/`
   and consumers get it on `PATH` through `package_info()`.
9. **OHOS ELF signing** at `package()` time via `binary-sign-tool
   -selfSign 1`, after `llvm-objcopy --remove-section .codesign`. `chmod
   755` alone is not enough for execution from the Conan package cache on a
   HarmonyOS device. When the signer is unavailable the recipe warns and
   continues rather than failing the build.

No source file is patched, so `conandata.yml` declares `patches: {}` and
no patch directory exists. No `__OHOS__` or other platform macro is
injected anywhere (R8 / PF5).

## Runtime scope on HarmonyOS PC

The delivered binary is an unmodified build of the upstream sources, and
everything the program does without global side effects works on OHOS:
version and help output, the full option table, configuration-file
parsing, the numeric range validators, and swap-directory filesystem
probing (all asserted by the test package).

Swap *activation* is a different matter and is deliberately not claimed.
Actually adding or removing a swapfile additionally requires all of:

- root privileges,
- a swap directory the process may write,
- a kernel built with `CONFIG_SWAP`,
- an `swapon`/`swapoff` path that the platform permits.

HarmonyOS PC is a desktop-oriented system that does not expose swap
management as a supported operation, so the daemon's steady-state
loop is expected to be of little practical use there even though the
program builds and runs correctly. This is recorded as a runtime scope
limitation, not an adaptation defect: no upstream code was removed,
stubbed or disabled to make the build succeed.

For the same reason the test suite does not attempt to create a real
swapfile — doing so would mutate global system state on whatever machine
runs the tests, which is not something a package test should do.

## Upstream test inventory (R51)

swapspace 1.18 has no automated test suite. Evidence collected from the
release tarball:

- `find . -type d -name 'test*'` → no `tests/` directory;
- `grep -rn 'TESTS\|check_PROGRAMS\|check-local' Makefile.am src/Makefile.am`
  → no matches, so `make check` has nothing to run;
- no `*.sh` / `*.py` test scripts, and no `.github/` / `.gitlab/` CI
  configuration in the tarball.

Upstream's own testing approach is manual: run the daemon and apply memory
pressure. `test_package/MANIFEST.yml` records this inventory with
`upstream_test_in_build: false` and an empty `upstream_tests` list.

## Test package

`test_package/test_swapspace.sh` runs the real installed binary and makes
**20 assertions over 20 distinct argument lists**, all passing (verified
programmatically):

- `--version` / `-V` print the packaged version and exit 0 (2 assertions);
- `--help` / `-h` print the description and document `swappath` and
  `lower_freelimit` (4 assertions);
- `-i` inspect mode over an existing swap directory exits 0, and over a
  missing directory exits 1 with `Could not get filesystem information`
  (2 assertions);
- a configuration file is accepted, applied, and works together with
  `-q`; verbose mode reports its configuration source; a *second* config
  file naming a different swap directory is the one actually probed; and
  the compiled-in default resolves to `/var/lib/swapspace` — asserted as a
  literal substring, so the doubled `/var/lib/lib/swapspace` fails (5
  assertions);
- a relative `swappath` in a config file is rejected with
  `Swap path is not absolute` (1 assertion);
- an unknown config item and an unknown command-line option are both
  rejected with `unknown configuration item` (2 assertions);
- the numeric range validators reject `freetarget` above 99, below 2, and a
  `max_swapsize` under its minimum, each with the expected
  `given value too large` / `given value too small` message (3 assertions);
- `-a -B -C -l -u` with in-range values are accepted together (1 assertion).

The script takes the binary path, the swap directory and the config
directory as arguments and uses only POSIX `sh`, `grep` and absolute
paths, so it does not depend on PATH lookups or a writable `/tmp` (the
read-only `/tmp` trap documented for HarmonyOS).

Two assertions are worth calling out because they were written wrong the
first time:

- `-v` with an explicit config file prints *no* `Using default
  configuration` line, because that message is only emitted when no config
  file was read. The assertion now points at a deliberately non-existent
  `-c` path, which is both hermetic (it cannot be perturbed by a real
  `/etc/swapspace.conf` on the test machine) and actually produces the
  message.
- The `default swappath is absent` assertion originally passed
  `-s "$SWAPPATH/does-not-exist"`, which made it byte-identical to the
  earlier missing-directory assertion and mislabelled what it checked. It
  now passes neither `-s` nor `-c`, so it exercises the real compiled-in
  default.
- That rewrite alone was still not enough to catch the `VARPREFIX` bug: an
  exit-code check cannot distinguish two different *nonexistent* paths, so
  both the correct and the doubled build passed it. The assertion now
  matches the literal `/var/lib/swapspace` in the daemon's error output,
  which the doubled `/var/lib/lib/swapspace` does not satisfy. Both claims
  were verified by building and running each variant under qemu.

## Local verification

Conan 2.29.1, profile `ohos-aarch64-wsl` for both host and build, matching
the CI profile's OHOS aarch64 clang 15 / libc++ settings:

```
conan create . --name=swapspace --version=1.18 \
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
```

- exit code `0`; source downloaded and SHA256 verified;
- all eight translation units compiled; only pre-existing upstream
  `-Wfortify-source` `sscanf` warnings, no errors;
- test_package executed: **20/20 assertions passed**;
- package layout: `bin/swapspace`, `share/man/man8/swapspace.8`,
  `etc/swapspace.conf`, `licenses/COPYING`;
- `readelf`: ELF64 AArch64, `DYN (PIE)`, `GNU_STACK RW` (NX enabled),
  `FLAGS_1: PIE`, single `NEEDED` entry `libc.so` — no host or toolchain
  library leaked into the binary.

The test_package binary ran for real: WSL has `qemu-aarch64` registered in
`binfmt_misc`, so the cross-compiled aarch64 ELF executes directly and
`can_run(self)` is true. The assertions above are genuine runtime
observations, not skipped cases.

`binary-sign-tool` is not present on this WSL host, so the packaged binary
has no `.codesign` section here. The signing step is exercised on the
HarmonyOS CI worker, where the tool exists at
`/data/service/hnp/bin/binary-sign-tool`.

## CI gate result (local run)

`CI_PACKAGES="archives/s/swapspace/1.18" zsh ci/conan/build_and_test.sh`
on this WSL host:

| Stage | Result |
|---|---|
| G0 knowledge graph integrity | pass |
| KC knowledge check | pass |
| JC junk check | pass |
| L0 quality gate | pass |
| L1 test execution | **fail (local artifact — see below)** |
| L2 smoke (`--version`) | pass |
| L4 security scan | pass (no patches) |
| L5 artifact baseline | pass |

L1's only failing sub-check is **L1e**, the destructive negative test. The
rest of L1 passes, and the packaged binary is genuinely covered: L1e moves
the package's `bin/` aside and re-runs `conan test`, expecting failure.

The local L1e red is an environment artifact of running the CI script on an
x86_64 WSL host, not a defect in the test. L1e invokes
`conan test ... -pr <ohos-aarch64 profile file>`, which sets only the
*build* profile; the *host* profile comes from conan's `default`. Here
`default` is the native `os=Linux arch=x86_64` detect, so
`can_run(self)` in test_package returns False, `test()` returns without
running anything, and the sabotaged run trivially "passes" — which L1e
reads as a fake test.

This was confirmed both ways:

1. **Replaying CI's exact command** with the default profile pointed at an
   OHOS profile (simulating the real CI worker, which *is* an aarch64 OHOS
   device): intact `bin/` → 20/20 assertions execute and pass; sabotaged
   `bin/` → 20/20 assertions fail and `conan test` exits 1. L1e therefore
   passes on CI.
2. **Precedent**: 2448 already-merged test packages use a `can_run()`
   guard (1300 in the `if not can_run(self)` form used here, 1052 in the
   inverse `if can_run(self)` form), including the two CLI packages whose
   structure this recipe follows — `cronutils/1.1` uses the same
   `if not can_run(self)` form and `jpegoptim/1.5.5` the inverse. Both are
   green in CI, so `can_run()` is True on the CI worker.

No change to the recipe is warranted for this; adding an unguarded
execution would make the package untestable on any genuinely cross-compiled
host.

## Knowledge draft

- `knowledge/drafts/DRAFT-swapspace-1.18-tarball-without-configure-direct-clang.md`
- `knowledge/drafts/DRAFT-swapspace-1.18-tarball-without-configure-direct-clang.kv`

It records the missing-`configure`/missing-`config.h` shape, the
`PACKAGE_*` define reconstruction, the shell-quoting trap for `-D` values
containing spaces, the separate-link requirement for `hog`, the
OHOS-runtime-libc vs SDK-link-stub-libc distinction (the SDK's `libc.so` is
a 72 KB link-time stub in which every symbol aliases one address, which
makes naive `nm` inspection of `swapon`/`swapoff` misleading), and the
20/20 consumer evidence.

## Next commands

Reproduce the full CI gate locally:

```sh
CI_PACKAGES="archives/s/swapspace/1.18" zsh ci/conan/build_and_test.sh
```

Single-package Conan create:

```sh
cd archives/s/swapspace/1.18
conan create . --name=swapspace --version=1.18 \
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
```
