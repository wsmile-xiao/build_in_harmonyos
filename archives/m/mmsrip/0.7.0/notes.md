# mmsrip 0.7.0 adaptation notes

## Package identity

mmsrip is a small (three .c files) MMS (Microsoft Media Services)
protocol client: it connects to `mms://` URLs and saves the ASF/WMV
stream to a file. Pure C, no third-party dependencies (libc sockets +
gethostbyname only), GPL-2.0-or-later, final upstream release from
2006-02-05.

## Upstream source

The tuxfamily.org hosting is dead: `http://download.tuxfamily.org/mmsrip/mmsrip-0.7.0.tar.gz`
returns a 267-byte 404 HTML page. The pristine tarball survives in
public distfile caches:

* FreeBSD ports distcache (net/mmsrip):
  `http://distcache.FreeBSD.org/ports-distfiles/mmsrip-0.7.0.tar.gz`
  — used as the conandata URL.
* ALT Linux Sisyphus SRPM `mmsrip-0.7.0-alt1.qa1.src.rpm` (pristine
  source inside).

Verification trail (three independent distros agree):

* sha256 `5aed3cf17bfe50e2628561b46e12aec3644cfbbb242d738078e8b8fce6c23ed6`
  — matches the Homebrew core mmsrip 0.7.0 formula.
* md5 `498a5ec1cd607e04f7d1b8232b839607` — matches the Arch Linux AUR
  PKGBUILD and the ALT Linux srpm.
* The FreeBSD distcache copy is byte-identical (`cmp`) to the tarball
  extracted from the ALT SRPM.

`https://distcache.FreeBSD.org` is DNS-poisoned in this environment
(resolves to a bogus IP; TLS handshake reset); the `http://` variant
works and was used for the fetch.

## Build system

2006-era Autotools (autoconf 2.59 / automake 1.9): the tarball ships a
pre-generated `configure` and `Makefile.in`, so no autoreconf is needed.

## OHOS adaptation

Two real OHOS issues were hit and fixed; both trace back to knowledge
already in the repo (path A, no new draft needed):

### 1. config.status confstat dir unwritable (umask 077 vs setgid HMDFS)

**Symptom**: `make` fails inside `config.status` — every write into the
`confstatXXXXXX` temp dir gets Permission denied:

```
config.status: creating Makefile
./config.status[259]: cannot create temporary file .../confstatXXX/subs.sed: Permission denied
```

**Root cause**: the conan cache and build dirs live on HMDFS, where
files are owned by uid 20001006 (file_manager) while the session runs
as uid 20020101 — access is only possible through the file_manager
group (dirs are 2771, setgid). autoconf 2.59's configure creates its
confstat temp dir with `umask 077 && mktemp -d`, which produces mode
**2700** — the group-write permission is masked off, so the very
process that created the dir can no longer write into it. autoconf
2.69+ changed this to `umask 022` upstream.

**Fix**: the same patch madplay 0.15.2b already ships
(`patches/0001-configure-umask-022.patch`,
"setgid hmdfs makes umask 077 dirs unwritable") — flip `umask 077` →
`umask 022` in both the mktemp and the fallback mkdir path of
configure. Verified: the resulting confstat dir is 2755 and config.status
completes.

### 2. mmsrip spins at 100% CPU instead of printing usage (unsigned plain char)

**Symptom**: any invocation that reaches the end of the argument list
(e.g. `mmsrip` with no arguments) spins forever at 100% CPU with zero
output. `mmsrip -v` / `-a` / `-h` work (they return from inside the
getopt switch).

**Root cause**: `main.c` stores the `getopt_long()` return value in a
plain `char c` and loops `while (c != -1)`. OHOS aarch64 clang defaults
plain char to **unsigned**, so the int -1 return is truncated to 255
and the loop never terminates. On the 2006 upstream platform (x86
Linux, signed char) -1 survived the truncation. Probe-compiled binary
shows `c=255` every iteration, and a two-line `char c = -1` repro
confirms `(char)-1 == 255` on this toolchain (`-fsigned-char` makes it
signed again).

**Fix** (E419 family — "Target plain-char signedness", same as
DRAFT-clipp / DRAFT-etl): inject `-fsigned-char` through the
AutotoolsToolchain so every translation unit uses one consistent
signed-char mode. No source patch, no OHOS ifdef, upstream semantics
on x86 preserved bit-for-bit.

### Non-issues analyzed and not triggered

The configure script never canonicalizes a triplet (no AC_CANONICAL_HOST, no config.guess/config.sub); passing --host is merely parsed into host_alias and otherwise ignored (apart from a --build warning).

* **AC_FUNC_MALLOC / AC_FUNC_REALLOC (rpl_malloc)** — the classic
  cross-compilation trap (when conftest cannot run, configure assumes
  `malloc(0)` returns NULL and defines `malloc` to `rpl_malloc`,
  which then fails to link because no `malloc.c` replacement exists).
  Analyzed and **not triggered**: the probes are *runtime* probes, and
  this is a native build — the conftest binaries run for real on the
  device, so `ac_cv_func_malloc_0_nonnull` resolves to `yes` honestly
  and no `rpl_malloc` is defined.

The `AutotoolsToolchain` is generated without any host triplet on
purpose; a comment in `conanfile.py` documents why.

`make -j1` is used (2006-era automake fragments are not parallel-make
safe with this toolchain — same pattern as madplay/macchanger).

## Upstream tests

None exist: no `TESTS`, no `check_PROGRAMS`, no `make check`/`make test`
target in the whole Autotools tree (verified by grepping `Makefile.am`,
`Makefile.in`, `configure`). Nothing is claimed as an upstream test;
all verification is the Conan consumer test_package (see
`test_package/MANIFEST.yml`), which runs the real binary on-device.

## test_package design

mmsrip is a network client, so the test suite is built from behaviors
that are deterministic offline (all verified against the upstream
source before writing the assertions). One deliberate design note:
`-v` returns 0 directly from inside the getopt switch — so `-g` (debug
log) must be exercised on its own, and the run then fails with usage
(exit 1) after the log has been created.

| # | command | expectation |
|---|---------|-------------|
| 1 | `--version` / `-v` | `mmsrip version 0.7.0` on stderr, exit 0 |
| 2 | `--about` | program/authors/GPL banner, exit 0 |
| 3 | `--help` | usage block incl. `-oFILE, --output=FILE`, exit 0 |
| 4 | (no args) | usage printed, exit 1 |
| 5 | `http://…` URL | `bad protocol (mms:// was expected)`, exit 1 — rejected in `mms_create` before any socket is opened |
| 6 | `mms://host` (no path) | `url seems to be malformed`, exit 1 |
| 7 | `-t mms://mmsrip.invalid/stream.asf` | real gethostbyname/DNS failure path → `unable to connect`, exit 1; `-t` mode must not create `stream.asf` |
| 8 | `-g debug.log` (alone) | debug log created with banner + `debug log begins now`; run then fails with usage, exit 1 (`-v` returns 0 from inside the getopt switch before `-g` is processed, so `-g` must be exercised on its own) |
| 9 | OHOS ELF check | ELF64 LE, `e_machine == EM_AARCH64`, PT_INTERP is `ld-musl-aarch64` |

Exit codes: `MMS_RET_ERROR` is `-1` and `main()` returns `ret*-1` → 1.

## shared/static

Not applicable: upstream ships an application only
(`bin_PROGRAMS = mmsrip`); no library is built, so there is no
shared/static choice to verify. Declared in `conanfile.py` via
`package_type = "application"`.

## Known risks

* The official download site is gone; the FreeBSD distcache is a
  community mirror (though triple-verified against Homebrew/Arch/ALT).
* `-t` success-mode (an actual live MMS server) is not tested — no
  such server is reachable from CI, and none is required to validate
  the OHOS port.
