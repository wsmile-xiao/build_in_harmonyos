# affiche 0.6.0 HarmonyOS adaptation notes

## Scope

Worktree: `C:\Users\ASUS\Documents\Codex\2026-08-25\d-harmonyos-md-harmonyos-d-harmonyos-12\work\build_in_harmonyos-affiche`
Branch: `feat/affiche-0.6.0`
Difficulty track: B类难度库 / 知识库拓展

Only `archives/a/affiche/0.6.0/` is touched in this round.

## Source identity

- Source package: Debian `affiche_0.6.0.orig.tar.gz`
- URL: `https://deb.debian.org/debian/pool/main/a/affiche/affiche_0.6.0.orig.tar.gz`
- SHA256: `4bb170c4c33cc84cc5ecb87c02395154426f4dd9d9e3a97d45782317b70e1de4`
- Debian dsc: `https://deb.debian.org/debian/pool/main/a/affiche/affiche_0.6.0-13.dsc`

## Upstream build analysis

Affiche is a GNUstep desktop application for sticky notes. The upstream tree is
centered on a top-level `GNUmakefile` and Objective-C sources plus localized
resources. There is no `configure`, `CMakeLists.txt`, `meson.build`, or upstream
`make check` target.

The intended build shape is:

```sh
make
make install
```

## Dependency check

Debian Build-Depends from `affiche_0.6.0-13.dsc`:

- `gnustep-make (>= 2.9.2-2)`
- `imagemagick`
- `libgnustep-gui-dev`

Repository findings:

- `gnustep-gui/0.31.1` is visible in the Conan registry and satisfies the
  Affiche 0.6.0 GNUstep GUI build. `gnustep-gui/0.32.0` has been merged
  separately but is not yet visible to PR CI workers.
- `gnustep-make/2.9.2`, `gnustep-base/1.31.1`, and `libobjc2/2.2.1` are the
  remaining GNUstep runtime/build pieces the app rides on.
- `imagemagick` is only needed for Debian icon conversion; the upstream app
  build does not need it.

## Test plan

There are no upstream tests. `test_package` is a bundle-layout smoke test:

- verify `share/GNUstep/Affiche.app` exists
- verify `bin/Affiche`, the bundle executable, `Info-gnustep.plist`,
  `Affiche.desktop`, `Localizable.strings`, and `*.tiff`
- avoid a headless GUI launch

## HarmonyOS validation

Device: `10.62.220.52:2222`, user `currentUser`.

Direct create passed on 2026-09-06:

```sh
conan create archives/a/affiche/0.6.0 \
  -pr:h=/storage/Users/currentUser/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 \
  -pr:b=/storage/Users/currentUser/build_in_harmonyos/ci/conan/profiles/ohos-aarch64 \
  --build=missing
```

Result:

- `affiche/0.6.0#0d3b173f7936ed9c5fea8da324496259`
- package id `ef9629e3eccfa8633b2c0e62cebb329b520e29fa`
- package revision `f007a15eb9ba3ce386a48b8232d32035`
- `test_package` passed the bundle smoke test

Targeted CI passed on 2026-09-06:

```sh
TMPDIR=/storage/Users/currentUser/tmp \
TMP=/storage/Users/currentUser/tmp \
TEMP=/storage/Users/currentUser/tmp \
TMPPREFIX=/storage/Users/currentUser/tmp/zsh \
CI_PACKAGES="archives/a/affiche/0.6.0" \
zsh ci/conan/build_and_test.sh
```

CI result:

- `L0_RESULT=pass`
- `L1_RESULT=pass`
- `L2_RESULT=skip`: Affiche is a GUI app and does not support `--version` or `--help`
- `L4_RESULT=pass`
- `L5_RESULT=pass`

The first PR CI runs against `gnustep-gui/0.32.0` were blocked in L0 because
that dependency version was not visible in the Conan registry. The recipe now
uses the published `gnustep-gui/0.31.1` package instead.

## Deferred worker commands

Re-run command:

```sh
conan create archives/g/gnustep-make/2.9.2 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
conan create archives/g/gnustep-base/1.31.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
conan create archives/g/gnustep-gui/0.31.1 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
conan create archives/a/affiche/0.6.0 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64
```

## Notes

- Keep changes limited to `archives/a/affiche/0.6.0/`.
- B类难度库知识库拓展已沉淀到
  `knowledge/drafts/DRAFT-affiche-gnustep-app-bundle-smoke.md`，覆盖 GNUstep
  app bundle smoke、R36 依赖门禁、GNUstep Make 脚本 wrapper、构建期
  `LD_LIBRARY_PATH` 污染规避等可复用经验。
- Use a unique env script name; do not reuse `conanbuild` because Conan already
  owns that name.
- If the app bundle installs under a different internal root on the worker,
  update the `test_package` to match the observed bundle shape rather than
  hardcoding a GUI launch.
- 2026-09-06: PR CI workers could not pass R36 with `gnustep-gui/0.32.0`
  because only `gnustep-gui/0.31.1` was visible in the Conan registry. The
  recipe was aligned to the published 0.31.1 GUI package and revalidated.
