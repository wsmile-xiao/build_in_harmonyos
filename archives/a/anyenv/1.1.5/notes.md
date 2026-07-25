# anyenv 1.1.5 OpenHarmony PC arm64 adaptation notes

- Official source: https://github.com/anyenv/anyenv, tag v1.1.5.
- Archive URL: https://codeload.github.com/anyenv/anyenv/tar.gz/refs/tags/v1.1.5.
- Build system: custom pure Bash script installation; no native compilation.
- Package layout keeps upstream `bin/anyenv -> ../libexec/anyenv` symlink so upstream path discovery continues to find `libexec` commands.
- `test_package` executes the packaged command with isolated `ANYENV_ROOT` and verifies `--version`, `root`, and `commands` behavior.
---

**编译结束**: 2026-07-14 19:10
**最终状态**: published
