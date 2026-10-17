# W0 report: vips 8.18.4

Date: 2026-08-07
Issue: 1909
Branch: feat/vips-8.18.4-1909

## Dependency check

Required for the prepared minimal core build:

- glib2/2.88.0: archive directory exists after rebasing onto current origin/main
- expat/2.8.2.1: direct core dependency for libvips XML support
- pcre2/10.45: consumed through glib2's published transitive dependency
- threads/libm: platform/system libraries

Remote product-registry checks not run:

```sh
conan download "glib2/2.88.0" -r=ohpcd --only-recipe
conan download "expat/2.8.2.1" -r=ohpcd --only-recipe
conan download "pcre2/10.45" -r=ohpcd --only-recipe
```

Reason: conan is not available in this Windows PATH.

## Source check

- Release URL: https://github.com/libvips/libvips/releases/download/v8.18.4/vips-8.18.4.tar.xz
- sha256: 2677bad6c422617fd1172d359c16af34e736965d042c214203a87187d26ff037
- SourceForge sha256sum mirror was reachable.
- Full source tarball download was slow/truncated locally, so no full local
  source extraction was completed.

## Local verification

Completed:

- Created isolated git worktree at D:\harmonyos\worktrees\vips.
- Added files only under archives/v/vips/8.18.4.
- Identified Meson build system and top-level dependency/option model.
- Prepared Conan recipe and non-empty test_package.

Not completed:

- direct registry-backed release CI without dependency overlays

## Shadow CI attempts

Device: currentUser@10.62.189.79:2222

Run 1:

- Runner directory: /storage/Users/currentUser/ohos-test-runs/codex-8.18.4-vips-8.18.4-1909-shadow-20260807-conan-20260807-111733-20297
- Result: failed in Conan dependency graph resolution.
- Reason: glib2/2.88.0 and expat/2.8.2.1 were not in the registry or device CI snapshot.

Run 2:

- Runner directory: /storage/Users/currentUser/ohos-test-runs/codex-8.18.4-vips-8.18.4-1909-shadow-20260807-conan-20260807-112429-23244
- Result: failed in Conan dependency graph resolution.
- Reason: glib/2.84.0 is not published and has no conanfile.py in the older device CI snapshot. expat/2.8.2 has a local recipe there, but the graph fails before it can be built.

Run 3:

- Job directory: /storage/Users/currentUser/ohos-users/codex/vips-8.18.4-1909-fresh-20260807
- Runner directory: /storage/Users/currentUser/ohos-test-runs/codex-8.18.4-vips-8.18.4-1909-fresh-20260807-conan-20260807-114632-32670
- Basis: fresh job from current origin/main with this vips patch applied cleanly.
- Extra setup: exported transitive pcre2/10.45 and zlib/1.3.1 recipes into the isolated Conan cache after the first fresh attempt found they were not exported automatically for glib2.
- Result: failed before vips was compiled.
- Reason: dependency expat/2.8.2.1 built objects successfully, then CMake failed to create `libexpat.so.1` and `libexpat.so` symlinks with `Permission denied`.

Run 4:

- Job directory: /storage/Users/currentUser/ohos-users/codex/vips-8.18.4-1909-with-expat1912-20260807
- Runner directory: /storage/Users/currentUser/ohos-test-runs/codex-8.18.4-vips-8.18.4-1909-with-expat1912-20260807-conan-20260807-123027-60132
- Basis: verification-only overlay, not a vips branch change. The job applied the expat issue #1912 fix first, then this vips patch.
- Extra setup: exported transitive pcre2/10.45 and zlib/1.3.1 recipes into the isolated Conan cache before running vips.
- Result: failed before vips was compiled.
- Progress: expat/2.8.2.1 built, installed, signed, and packaged successfully as `libexpat.so`; the previous `libexpat.so.1` symlink failure did not recur.
- Reason: dependency pcre2/10.45 failed when executing its generated/source `configure` script: `/system/bin/sh: .../pcre2.../configure: Permission denied`.

Previous dependency blockers:

- The expat symlink failure was split into dependency issue #1912; the
  follow-up overlay uses expat/2.8.2.1.1.
- The pcre2 `configure: Permission denied` failure was split into dependency
  issue #1913; the follow-up overlay uses pcre2/10.45.1.1.
- Do not include expat, pcre2, glib2, or zlib changes in this vips PR.

Run 5:

- Job directory: /storage/Users/currentUser/ohos-users/codex/vips-8.18.4-1909-with-expat1912-20260807
- Runner directory: /storage/Users/currentUser/ohos-test-runs/codex-8.18.4-vips-8.18.4-1909-with-expat1912-pcre21913-r8-20260807-conan-20260807-155851-60776
- Basis: verification overlay using expat/2.8.2.1.1 from issue #1912 and pcre2/10.45.1.1 from issue #1913.
- Result: passed with `rc=0`.
- Gate summary: L0 pass, L1 pass, L4 pass, L5 pass. L2 skipped with non-blocking warnings because the installed CLI tools returned non-zero for `--version/--help`.
- Evidence: `conan create` built and packaged `vips/8.18.4`, executed `./test_vips`, and R34 confirmed the test fails when `bin/`, `lib/`, and `include/` are removed.

Official PR CI follow-up:

- PR CI #15549 failed before building vips because expat/2.8.2.1.1 and
  pcre2/10.45.1.1 were not published in the registry. The release-facing recipe
  was updated to use expat/2.8.2.1 and to remove the pcre2 override so glib2 can
  use its pcre2/10.45 transitive dependency.
- The follow-up dependency recipes from issues #1912 and #1913 remain useful
  shadow-CI evidence, but are no longer required by this vips PR.

## Next commands

```sh
CI_PACKAGES="archives/v/vips/8.18.4" zsh ci/conan/build_and_test.sh
```

```sh
/path/to/run-ohos-shadow-ci.sh archives/v/vips/8.18.4
```
