# DXX-Rebirth 0.6 OHOS adaptation notes

## Version mapping

The requested Conan reference is `dxx-rebirth/0.6`. The user confirmed that it maps to the official upstream `0.60.0-beta2` tag.

## Build configuration

- Build both `d1x-rebirth` and `d2x-rebirth` with upstream SCons.
- Use `sdl12-compat/1.2.68` because this upstream release targets the SDL 1.2 API; the compatibility package supplies that API over the published SDL2 runtime.
- Disable SDL_mixer and OpenGL to keep the initial OHOS port dependency-complete.
- Use legacy screenshots to avoid the optional libpng dependency.
- Disable precompiled headers for reproducibility with the old build system.
- Backport six official upstream Python 3 fixes and pin SCons 4.4.0; SCons 4.5+ changes `CPPDEFINES` to `deque`, which this release does not support.
- Remove the legacy `static_assert` macro wrapper under C++11 so modern OHOS libc++ assertions containing commas compile as native C++.
- Read `allow_nullptr` from its policy type instead of a function argument so Clang can evaluate the compile-time validity constraint.
- Backport upstream `d056611` to expose the exception-policy trait required by explicit template instantiation under Clang.
- Add `ohos` to SCons `host_platform`; Conan's OHOS profile must be passed through to the build system instead of being rejected or impersonated as Linux.
- Let Conan's compiler executable carry the OHOS target configuration; adding a second explicit target flag breaks dependency header probes on CI.
- Set the SCons construction environment `SHELL` to `/system/bin/sh` on OHOS because CI's inherited `/bin/sh` path is unavailable to spawned build actions.
- Use `sdl12-compat/1.2.68` and `physfs/3.2.0.1`, both published in `ohpcd`.
- Do not define `__linux__` manually; the OHOS toolchain and the upstream POSIX path are used without impersonating a Linux target.
- Validate the actual SDL video initialization, software-rendering surface, frame flip, and event queue used by the engines with the published OHOS SDL compatibility dependency.

## Tests

Upstream `0.60.0-beta2` contains no standalone unit or integration test suite. The Conan consumer test therefore validates the real `-help` command path for both installed game engines. It does not require proprietary game data.

## Findings

- ✅ L3: Python 3/SCons compatibility and Clang fixes are captured in this version's recipe and patch series.
- ✅ L3: The upstream test boundary, two command tests, and SDL runtime test are captured in `reports/test-report.md`.

---

**编译结束**: 2026-08-25 00:22
**最终状态**: built
