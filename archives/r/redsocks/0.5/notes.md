# redsocks 0.5 Adaptation Notes

## Build Environment
- Build system: makefile
- Date: 2026-09-17 (round 3 fix; original 2026-08-08)
- Compiler: clang 15 (from profile `tools.build:compiler_executables`)
- Status: built + test_package green (local conan create with ci profile)

## Build Steps
1. Source: https://github.com/darkk/redsocks/archive/refs/tags/release-0.5.tar.gz
2. Conan recipe: AutotoolsToolchain + AutotoolsDeps generators, `make -j1` in
   source folder with conanbuild env (CC/CPPFLAGS/LDFLAGS flow from env;
   upstream Makefile default `LIBS := -levent_core` links the shared
   libevent_core)
3. Runtime: `requires(..., run=True)` propagates libevent's libdir to
   consumers' VirtualRunEnv (LD_LIBRARY_PATH); link step also embeds RPATH
   to the libevent lib dir so bare invocations (L2-style smoke) work.

## Issues
| # | Issue | Root Cause | Solution |
|---|-------|-----------|----------|
| 1 | -levent_core link fail (round 1) | Conan libevent package layout | Makefile default `-levent_core` resolves via AutotoolsDeps `-L` flag; libevent_core.so exists in package |
| 2 | config.h generation | Makefile uses `uname`, device returns `HarmonyOS` | 0001-Makefile.patch: `Linux*|HarmonyOS)` case → USE_IPTABLES |
| 3 | gen/version.c | git describe fails on tarball | Non-git fallback in upstream Makefile: outputs `redsocks/0.5` |
| 4 | ConanException: `tools.build:compiler_executables:c` does not exist (round 2 regression, build() line 53) | Recipe rewrite used invalid sub-key conf access; correct API is the dict conf `tools.build:compiler_executables` | Replaced with AutotoolsToolchain (reads the conf properly and sets CC) — never access dotted sub-keys of `tools.build:compiler_executables` |
| 5 | `make` failed "No targets specified and no makefile found" | `self.run()` without cwd executes in build folder (`build-release`), sources live in source folder under this conan's basic_layout | `self.run("make -j1", cwd=self.source_folder, env="conanbuild")`; package() copies from source_folder |
| 6 | test_package exit 127: `Error loading shared library libevent_core-2.1.so.7` | Binary links SHARED libevent; conanrun env only had PATH because VirtualRunEnv composes cpp_info-derived env only for requires with `run=True`; the transitive redsocks→libevent edge defaulted to run=False | `self.requires("libevent/2.1.12", run=True)` in requirements() + embedded `-Wl,-rpath,<libevent libdir>` in LDFLAGS |
| 7 | test.sh wrote to /tmp → "Read-only file system" (E002) | OHOS /tmp is read-only | `mktemp -d "${TMPDIR:-/tmp}/redsocks-test.XXXXXX"` + cleanup trap (daemon package pattern) |
| 8 | Old test.sh grep matched its own error output (false positive) | `redsocks` (no args) error text contains the binary path containing "redsocks" | Assert on real behavior instead: `-v` prints version (exit 0), `-t` valid config → exit 0 silently, `-t` invalid config → exit 1 |

## Upstream Tests (R51)
- Upstream `make test` (tests/run) requires root (iptables), Docker and a Linux
  VM environment; not runnable on OHOS. tests/ contains ~40 bash-driven
  integration cases — none portable to the device as-is.
- test_package provides 3 smoke assertions (version, valid config, invalid
  config rejection).

## Dependencies
| Dep | Version | Source |
|-----|---------|--------|
| libevent | 2.1.12 | Conan ohpcd (shared libs; run=True) |

## Round 3 Change Summary (2026-09-17, wl-4647)
- conanfile.py: fixed invalid conf access (#4), cwd/source_folder handling (#5),
  run=True + RPATH for shared libevent runtime (#6)
- test_package/test.sh: TMPDIR-safe scratch dir (#7), real behavior assertions (#8)
- test_package/MANIFEST.yml: description aligned with new test.sh
- Removed `.submit-state.json` from git tracking (runtime state, not archived
  on main by any other package)
