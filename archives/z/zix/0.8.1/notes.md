# zix 0.8.1 HarmonyOS Preflight Notes

Date: 2026-08-25
Branch: feat/zix-0.8.1-codex
Package path: archives/z/zix/0.8.1

## W0 Dependency Check

`python scripts/ohc-run.py resolve-deps zix 0.8.1 --dry-run` reported that
zix prerequisites are already available/no split dependency is needed.

Upstream Meson only uses the system thread dependency. There are no Conan
package dependencies to adapt before zix.

## Source

The official download URL `https://download.drobilla.net/zix-0.8.1.tar.xz`
returned 404 on 2026-08-25. `https://download.drobilla.net/zix-0.8.2.tar.xz`
returned 200, so the 0.8.1 tarball appears to be absent rather than a naming
pattern issue.

GitLab tags include `v0.8.0` and `v0.8.2`, but no `v0.8.1`. This recipe pins
the existing upstream GitLab archive used by prior zix work:

- URL: `https://gitlab.com/drobilla/zix/-/archive/a4fab09/zix-a4fab09.tar.gz`
- sha256: `858b93002977e9b4d5dd95cccb4732f6c2a8afbd94f38374fcb311e751d8296d`
- Meson project version: `0.8.1`

## Build System

zix is a Meson C project.

Relevant Meson options:

- `default_library`: mapped from Conan `shared`
- `checks`: enabled
- `threads`: enabled
- `tests`: enabled
- `tests_cpp`: auto
- `benchmarks`, `docs`, `html`, `singlehtml`: disabled
- `lint`: false

The recipe injects `llvm-ar`/`llvm-ranlib` into Conan's Meson native/cross
machine files when Conan's MesonToolchain omits them, matching existing OHOS
Meson recipes in the repository.
For shared builds, the recipe also ensures the build/install tree contains
`libzix-0.so.0` and `libzix-0.so` aliases for the versioned
`libzix-0.so.0.8.1` library, so OHOS runtime loading and consumer linking work.

## Tests

The recipe runs the upstream suite with:

```sh
meson test -C <build_folder> --print-errorlogs
```

The upstream suite registers up to 24 tests when thread and C++ probes are
available. The known OHOS differences are `test_filesystem` link-creation
checks on restricted filesystems. The hard-link patch keeps the test enabled and
only accepts `ZIX_STATUS_BAD_PERMS` alongside the upstream accepted hard-link
failure statuses. The symlink patch keeps canonical path testing enabled, but
skips the symlink-specific branch when symlink creation returns
`ZIX_STATUS_NOT_SUPPORTED` or `ZIX_STATUS_BAD_PERMS`.

The consumer `test_package` builds a C executable against `zix::zix` and checks
digest determinism, status strings, string views, path joins, and allocator
round-trip behavior.

## Knowledge Drafts

- `knowledge/drafts/DRAFT-zix-meson-build-tree-soname-alias.{kv,md}` records
  the Meson build/install-tree SONAME alias issue exposed by zix shadow CI.
- `knowledge/drafts/DRAFT-zix-hmdfs-filesystem-link-subtests.{kv,md}` records
  the restricted hardlink/symlink filesystem-test behavior on OHOS/HMDFS.
