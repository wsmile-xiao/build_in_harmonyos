# gpgme 1.24.0.1 OHOS Conan Port Notes

## Scope

- Builds the GPGME C library plus the C++ and Qt6 bindings used by KDE PIM:
  `gpgme::gpgme`, `Gpgmepp`, and `QGpgmeQt6`.
- Uses the upstream autotools build with `--enable-languages=cpp,qt6`.
- Builds and installs only `src`, `lang/cpp/src`, and `lang/qt/src` because
  upstream `make check` requires a real GnuPG runtime that is not packaged for
  this OHOS environment.

## Key Adaptations

- Patches `config.guess`, `config.sub`, and `configure` for linux-ohos and
  HMDFS temporary directory permissions.
- Supplies local config wrappers for `gpgrt-config` and `libassuan-config`
  because the dependency package scripts and metadata contain non-relocatable
  paths.
- Rewrites `gpg-error.pc`, Qt6 `.pc` files, and dependency `.la` files in a
  build-local `config-overrides` directory.
- Resolves shell, compiler tools, `pkgconf`, and `moc` from the Conan profile
  and dependencies instead of hardcoding one runner layout.
- Replaces upstream installed CMake configs with relocatable configs for
  `gpgme`, `Gpgmepp`, and `QGpgmeQt6`; upstream configs point at `/lib` and
  `/include` after DESTDIR installation.

## Verification

Command:

```bash
conan create archives/g/gpgme/1.24.0.1 -pr:h=<ohos-aarch64> -pr:b=<ohos-aarch64> --build="gpgme/*"
```

Result:

- Package reference:
  `pending: republished as gpgme/1.24.0.1 because gpgme/1.24.0 is already published as C-only`
- `test_package` configured a CMake consumer with `find_package(gpgme)`,
  `find_package(Gpgmepp)`, `find_package(QGpgmeQt6)`, and
  `find_package(Qt6 COMPONENTS Core)`.
- CTest passed `1/1`.
- Direct smoke test printed:

```text
PASS: gpgme 1.24.0
PASS: gpgmepp 1.24.0
PASS: qgpgme 1.24.0
```

Fallback runner log:
`~/ohos-users/codex-a/akonadi-25.12.3-testenv-r2-20260826/repo/build_in_harmonyos/.ci_logs/conan_build_gpgme_1.24.0_r11_oldport.log`

## 2026-09-01 republish note

The published `gpgme/1.24.0` package only provides the C binding and cannot
satisfy KDE PIM consumers that call `find_package(Gpgmepp)` and
`find_package(QGpgmeQt6)`. This recipe is therefore submitted as
`gpgme/1.24.0.1` to avoid the R37 same-version collision while keeping the
upstream source version at 1.24.0.
