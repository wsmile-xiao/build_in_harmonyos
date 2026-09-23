# libmarpa 11.0.13 adaptation notes

## Upstream identity

- Source: GitHub tag `v11.0.13` of `jeffreykegler/libmarpa`
  (`https://github.com/jeffreykegler/libmarpa/archive/refs/tags/v11.0.13.tar.gz`),
  SHA256 `cb3c7f47d9ee95de967838ea0ecc380ffacfdfd8ec2c3d7cc2a6acaa4cc9597b`.
- The repository is a *literate-programming* source tree: the distributed C
  sources (`marpa.c`, `marpa.h`, ...) are generated from `.w` (CWEB) files by
  `ctangle`, then assembled into an Autotools "stage" directory by
  `etc/copier.pl`, from which `autoreconf` + `make dist` produces the
  `libmarpa-11.0.13.tar.gz` ac_dist that is actually configured and built.
- No runtime dependencies; the library only needs libc.
- License: LGPL-3.0-or-later (`work/obs/COPYING.LESSER`, Version 3; the CWEB
  sources themselves carry the MIT-style Kegler permission notice).
- Autotools (not CMake) is the authoritative build system for the library;
  the `cmake/` directory is a community-side CMake wrapper that does not
  generate the sources and is not used by the recipe.

## Generation chain (what build() does)

The upstream release tarball does NOT contain a pre-built Autotools tree; the
recipe reproduces the canonical upstream chain (top-level `Makefile` target
`ac_dist`) inside `build()`:

1. `make libmarpa_version.sh` + `work/etc/LIB_VERSION` (top-level Makefile
   rules; pure shell, version numbers 11.0.13).
2. `dev/api.texi` + `dev/internal.texi` from their `.premenu` sources: the
   upstream make rule is `sed` (splice a DO-NOT-EDIT header) + `emacs -batch`
   (reorganize `@menu` blocks for human reading). The build host has no emacs;
   the recipe runs the sed part byte-for-byte and skips the menu rewrite —
   verified harmless because the texi consumers (`public/texi2err.pl`,
   `texi2event.pl`, `texi2step.pl`) match only `@deftypevr`/`@deftypefun`/
   `@strong` lines, never `@menu`/`@node`. IMPORTANT: `work/ami/` has its own
   `api.texi`/`internal.texi` checked into git (they carry the friend-API
   `@deftypefun` declarations that `marpa_ami.h.p50` is generated from);
   they must not be overwritten with the dev/ variants.
3. Doc placeholders: the stage copier list requires `dev/marpa.pdf`,
   `ami/marpa_ami.pdf`, `doc/api_html.tar`, `doc1/api.pdf`/`api.info`/
   `api.html`. The build host has no pdftex/makeinfo/texi2any/texi2html, so
   the recipe creates small "see the website" placeholder payloads before
   running `make sources` (dev/ami's default `all` targets include the PDF
   rules, so a pre-existing file lets make skip them). Documentation-only
   payloads — no code is affected; the installed headers/libs are identical.
4. CWEB tangling runs **per subdirectory** (`dev/`, `ami/`, `tavl/`, `public/`,
   `ac/`) via each dir's `sources`/`all` target with ctangle from
   `tool_requires cweb/4.12.2`. The upstream `work/Makefile` `sources` target
   is a shell for-loop over the subdirs running each subdir's default `all`;
   that loop is used instead of the loop itself because (a) dev/all and
   ami/all drag in the cweave/pdftex PDF rules which cannot run on this host,
   and (b) the for-loop masks subdir failures (see E546 knowledge entry) —
   running the subdirs directly surfaces any real generation error.
5. `perl etc/copier.pl < work/ac/copier.list` assembles `work/stage/` exactly
   per upstream's list.
6. The upstream `Makefile.am` dist-hook runs `git log -n 5 >> GIT_LOG.txt`
   inside the stage tree. Upstream runs this from a git checkout; the Conan
   build dir is not one, so the recipe `git init`s the stage tree and commits
   the staged snapshot first — the appended GIT_LOG.txt then truthfully
   records this dist snapshot (GIT_LOG.txt is provenance documentation only).
7. `autoreconf -iv` + `sh configure` + `make dist` in `work/stage` produces
   `libmarpa-11.0.13.tar.gz` — upstream's own ac_dist mechanism. Automake's
   dist-gzip rule hardcodes `gzip --best`; the OHOS build host ships a toybox
   gzip that rejects long options (E402), so the recipe puts a tiny gzip
   front-end mapping `--best` → `-9` on PATH for that one command.
   Between `autoreconf` and `sh configure`, the recipe rewrites the umask of
   the temp-dir creation in the just-generated `work/stage/configure`
   (E114, see "HMDFS temp-dir umask (E114)" below).
8. The tarball is unpacked and built with the regular Autotools flow
   (`configure --host=aarch64-unknown-linux-ohos`, `make`, `make check`,
   `make install`) — exactly like an upstream release build.

Configure is invoked with `--prefix=<package_folder>` only (no DESTDIR, per
R20); AutotoolsToolchain's literal `${prefix}/lib`-style dir args are dropped
because the manual configure invocation does not eval-expand them.

No source patches are applied. Upstream's bundled `config.sub`/`config.guess`
(timestamp 2023-09-19) already recognize `aarch64-linux-ohos` natively, so not
even a config.sub patch is needed.

## HMDFS temp-dir umask (E114)

Autoconf-generated `configure` scripts create their `confXXXXXX` scratch
directory with a restrictive umask inside the temp-dir creation expression.
The build resolves the repository's patched `autoconf/2.72` (whose AS_TMPDIR
patch adds a `linux-ohos` case but keeps `umask 077` on all three branches —
`mktemp -d`, its `mkdir "$tmp"` fallback, and the non-ohos fallback path);
plain upstream m4sh instead emits `umask 000` twice. On the HarmonyOS PC
HMDFS build tree every directory is setgid, so `umask 077` produces
`drwx--S---`, and the resulting `config.status` dies with
`./confIOojAN/subs1.awk: Permission denied` /
`could not setup config files machinery` when writing its awk fragments into
that directory. `umask 022` yields `drwxr-s--x`, which is known good.

The fix is scoped to the dist-generation step only: right after
`autoreconf -iv` and before `sh configure`, `_patch_autoconf_hmdfs_umask()`
rewrites exactly the empirically verified AS_TMPDIR temp-dir creation layouts
in the generated `work/stage/configure` — each with the exact occurrence
count its generator emits:

- repository `autoconf/2.72` with the linux-ohos AS_TMPDIR patch (case
  block): `(umask 077 && mkdir "$tmp")` ×2 + `(umask 077 && mktemp -d
  "./confXXXXXX")` ×1
- plain upstream 2.72 m4sh (what a stock autoreconf 2.72 emits, e.g. the CI
  worker): `(umask 077 && mkdir "$tmp")` ×1 + `(umask 077 && mktemp -d
  "./confXXXXXX")` ×1
- local m4sh with the relaxed `umask 000` text: the `umask 000` equivalents
  of the previous form ×1 each

All of them become `umask 022`. It is fail-closed: the rewrite is confined
to the AS_TMPDIR block between `# Create a (secure) tmp directory` and
`ac_tmp=$tmp` — a `umask 077`/`umask 000` anywhere else in the file, an
occurrence-count combination that is not exactly one known layout, several
layouts at once, or a residual `umask 077`/`umask 000` after the rewrite
raises `ConanInvalidConfiguration` instead of running an unpatched configure
(no global replace). A configure already carrying one of the known relaxed
022 layouts (a previous run of the helper) is accepted unchanged, making the
patch idempotent. The `make dist` tarball then carries the 022 form, so the
final `configure` run in `build-release` inherits it and no further action
is needed. Upstream sources are never modified.

## Upstream test contract

`make check` runs Russ Allbery's C TAP harness over `tests/TESTS`:

- 8 test programs: `rule1`, `trivial`, `trivial1`, `depr_unvalued`, `nits`,
  `issue92a`, `issue92b`, `issue92c`
- 896 assertions total (`Files=8, Tests=896`), verified on OHOS aarch64 for
  BOTH the shared and the static package.

The upstream test programs link the **static** `libmarpa.a` by design
(`tests_simple_*_LDADD = tests/tap/libtap.a libmarpa.a` in `Makefile.am`), so
`make check` exercises the static library even in the shared build; the shared
library is validated by the consumer test_package.

## Shared vs static

`LT_INIT` with default arguments builds both flavors; the recipe restricts
this via `--enable-shared/--enable-static` per the `shared` option:

- shared: `lib/libmarpa-11.0.13.so` (SONAME `libmarpa-11.0.13.so`, `-release
  11.0.13` LDFLAG) + `libmarpa.so` symlink, NEEDED only `libc.so`
- static: `lib/libmarpa.a`

Both verified end-to-end: `conan create` with `-o shared=False` and
`-o shared=True`, each running the 896-assertion upstream suite plus the
consumer test_package (real grammar: version contract, symbols, rules,
precompute, recognize 2 tokens, bocage→order→tree→value chain, documented
error path `MARPA_ERR_INVALID_RULE_ID`), all assertions passing, executed via
bash (mksh cannot exec ELF binaries directly).

ELF verification (shared): ELF64 AArch64 `DYN`, INTERP
`/lib/ld-musl-aarch64.so.1` (musl), NEEDED `libmarpa-11.0.13.so` +
`libc.so`, no RPATH/RUNPATH needed (system loader resolves libc; the recipe
exports `libdir` via package_info for consumers).

Upstream does not install a usable pkg-config file (the shipped
`libmarpa.pc` is a CMake `configure_file(@ONLY)` template whose
`@PROJECT_NAME@`-style placeholders are left unsubstituted by Autotools), so
the recipe does not install one either; `package_info()` carries the flags.

## OHOS specifics

- `--build=aarch64-unknown-linux-ohos --host=aarch64-unknown-linux-ohos`
  passed explicitly (config.guess on the build host returns the same triplet,
  but passing it avoids host-probe surprises under HMDFS).
- `make` runs with `-j1` (E074: HMDFS jobserver fifo EPERM).
- Test binaries and the test_package binary are executed via `bash -c`
  in the recipe's `test()`; upstream `make check` runs under the build
  environment shell.
- Upstream warning flags include `-ansi -pedantic` when `GCC` is detected;
  clang identifies itself as GCC for these probes. The build completes with
  warnings only (e.g. clang's `-L` unused-during-compilation note), which is
  upstream behavior, not an adaptation failure.
- The Conan Release profile adds `-DNDEBUG`; libmarpa builds cleanly under
  it (the previous session's manual build had no `-DNDEBUG`, so this was
  explicitly re-verified through the full Conan profile flags).

## Reproduction

```
conan create archives/l/libmarpa/11.0.13 \
  -pr:h=~/.conan2/profiles/ohos-aarch64-device \
  -pr:b=~/.conan2/profiles/ohos-aarch64-device \
  -o shared=False --build=libmarpa/*
# same with -o shared=True
```

(The reproduction profiles point the compiler and `CONFIG_SHELL` at the
local host layout while keeping the CI profile's settings; on a CI worker
`ci/conan/profiles/ohos-aarch64` is used for both `-pr:h` and `-pr:b`.)
