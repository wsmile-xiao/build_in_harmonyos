# pkgconf 3.0.6 adaptation notes

## Scope

- Activity: dependency (`开源鸿蒙PC专项积分赛-依赖`).
- Branch: `feat/pkgconf-3.0.6`.
- Source: official `pkgconf-3.0.6.tar.xz` release archive.
- Source SHA-256: `c88a653fbabfa2a5857a30f6b6ad6c40dbacc3b7c72cc066e5c7dc4571cbddaa`.
- Build system: Meson.
- External Conan dependencies: none.
- Recursive dependency classification: simple; the upstream build files declare no
  external `dependency()` or `subproject()` edges.

## Build decisions

- Build `libpkgconf` statically without forcing a fully static libc link.
- Preserve the tested 3.0.5 portability patches and replay them against the 3.0.6
  source only after a clean patch applicability check.
- Install the four upstream command-line tools: `pkgconf`, `bomtool`, `spdxtool`,
  and `pccritic`.
- Keep the package-level `commands.json` entry because this recipe installs
  executables.
- Use one build/test job to stay within the local CPU budget.

## Validation status

W0 source/dependency inspection passed. Local Conan creation, complete upstream
tests, consumer tests, target validation, and platform submission remain pending
until the 3.0.6 candidate is built and its exact evidence is frozen.

## Safety boundary

If a future source or Conan inspection reveals a complex GUI/platform dependency or
a large target binary closure, stop this dependency and release any unbound
downstream task instead of continuing recursively.
---

**编译结束**: 2026-09-03 19:45
**最终状态**: built
