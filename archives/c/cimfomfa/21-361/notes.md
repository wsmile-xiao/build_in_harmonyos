# cimfomfa 21-361 adaptation notes

## Source and build

- Upstream: https://github.com/micans/cimfomfa
- Tag: `21-361`, commit `b3a0c1685a6e47d892a32cec683fcef07148b610`
- Language: C (accepted for the task's C++ lane by the C/C++ family rule)
- Build system: Autotools
- Runtime dependencies: none; the resulting static archive requires the platform math library.
- Build dependency: `automake/1.18` supplies `automake` and `aclocal` while
  regenerating the files omitted from the Git tag.
- Product: `libtingea.a` plus 21 public headers in `include/tingea/`.

The GitHub tag is a developer-source snapshot: it includes `configure.ac.in`
and the Automake inputs but deliberately omits `VERSION`, `configure.ac`,
`configure`, `aclocal.m4`, and `config.h.in`. The recipe recreates VERSION and
configure.ac from upstream's own `shed/setversion` logic, then runs
`autoreconf -fi`. No downstream source patch is needed.

## Duplicate and dependency preflight

- No cimfomfa archive exists on fetched `upstream/main`.
- No origin/upstream branch matching `cimfomfa` was found.
- The public PR dashboard contains no cimfomfa entry. Exact authenticated API
  search was unavailable because this workstation has no GitCode token.
- `conan download cimfomfa/21-361 -r=ohpcd --only-recipe` returned
  `system acceleration policy not enabled`, the registry's known response for
  an unpublished recipe (knowledge E477).
- The package has no Conan runtime `requires` dependencies.
- `automake/1.18` was downloaded successfully from the `ohpcd` registry and
  is declared as a `tool_requires` dependency.

## Upstream test inventory and native baseline

Upstream README explicitly says there are no unit tests. `make check` runs
zero registered tests. `src/trumpet/Makefile.am` declares 16 noinst testing and
diagnostic programs; all 16 compiled successfully on the native macOS baseline.

Nine representative programs were actually executed and passed (9/9):
`cff_pagesize`, `cff_link`, `cff_bitpat`, `cff_let`, `cff_tst`,
`cff_unit_ceilfloor`, `cff_optoid`, `cff_match`, and `cff_read`.

Native baseline commands:

```text
bash shed/setversion 21-361
autoreconf -fi
../configure --prefix=<temporary-prefix>
make -j2
make check
make install
```

## Consumer coverage

The Conan test package compiles as C, links `cimfomfa::cimfomfa`, and performs
nine failure-checked assertions over `mcxTing` string allocation/append/free
and duplicate-aware `mcxBsearchFloor`/`mcxBsearchCeil` behavior.

An independent HarmonyOS-specific executable, `test_harmonyos.c`, adds ten
failure-checked assertions. It requires the `__OHOS__` macro and aarch64 target,
reads the real OHOS page size and UID through libc, and uses the page-size value
with the packaged `mcxBsearchFloor`/`mcxBsearchCeil` APIs while also validating
`mcxTing` allocation, append, content, and free behavior.

## CI follow-up

PR #8929 build #42331 reached `conan create` on the OHOS worker but initially
failed in `autoreconf -fi` because `aclocal` was absent from the minimal worker
image. The source download, structural gates, package graph, and OHOS profile
selection had already succeeded. The recipe now follows the repository's
existing Autotools bootstrap pattern and declares the published
`automake/1.18` package as a build requirement; cimfomfa does not use Libtool.

Build #42347 confirmed that fix: `automake/1.18` was downloaded and
`autoreconf -fi` completed. Configure then failed when `config.guess` attempted
to write `dummy.c` in an HMDFS-backed mode-0700 temporary directory. This is
the repository's documented E129 `config.guess` variant. For OHOS builds the
recipe now passes the native `aarch64-unknown-linux-ohos` build triplet, which
uses Autoconf's supported explicit-build path and skips the failing probe;
`--host` remains unset so the build stays native and its test programs run.

Build #42360 confirmed that configure accepted the explicit triplet and
completed every feature check. It then failed while the generated
`config.status` created `./confXXXXXX/subs1.awk`: Autoconf's embedded
`umask 077` produces an HMDFS directory that is not writable by the mapped
worker UID. After `autoreconf`, the recipe now rewrites those two generated
temporary-directory commands to `umask 022` on OHOS, following the repository's
E129/E011 fix. This still blocks writes by group and other users while allowing
the worker owner to create the generated configuration files.

Build #42369 subsequently passed the Conan package build, the nine upstream
programs, and the installed-package consumer on the HarmonyOS worker. The new
HarmonyOS-specific executable is included for the next CI run to satisfy the
event review requirement with a real platform test rather than a declaration.

## Environment notes

The local workstation does not contain the HarmonyOS PC compiler paths from
`ci/conan/profiles/ohos-aarch64`. Target verification therefore must be run by
the repository's real HarmonyOS worker; macOS results are recorded only as the
upstream/native baseline and are not claimed as W3.
