# pulseaudio-ctl 1.70 适配笔记

## 编译环境
- 构建系统: makefile (simple Makefile, no configure step)
- 编译日期: 2026-06-04
- 编译器: clang/clang++ (not used for shell script project)
- 状态: published

## 编译步骤

pulseaudio-ctl is a simple shell script wrapper for PulseAudio. No configure step required.

1. `make PREFIX=$DEFAULT_PREFIX` — generates the shell script from pulseaudio-ctl.in template (substitutes @VERSION@ and @SKELDIR@)
2. `make install DESTDIR=$TEST_PREFIX PREFIX=$DEFAULT_PREFIX` — staging install
3. `make install PREFIX=$DEFAULT_PREFIX` — final install to ~/usr/local
4. `ohc-run.py package pulseaudio-ctl 1.70` — packaging

No test suite available (no `make check` target). The project is a pure shell script and requires pactl/pacmd (PulseAudio utilities) at runtime.

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `install` command not found | OpenHarmony lacks GNU coreutils `install` command by default | Installed coreutils 9.10 precompiled package; `ginstall` is available as `install` via symlink |
| 2 | `#!/bin/bash` shebang fails | bash not at `/bin/bash` on OpenHarmony (at ~/usr/local/bin/bash) | Changed shebang to `#!/usr/bin/env bash` in pulseaudio-ctl.in (tracked via track-edit) |
| 3 | Version 1.99 not found | Original URL (nicoulaj/pulseaudio-ctl v1.99) doesn't exist; repo is at graysky2/pulseaudio-ctl, latest version is 1.70 | Used v1.70 from graysky2/pulseaudio-ctl |
| 4 | G4 verify-build failed initially | manifest.yaml missing `build_system` top-level field | Added `build_system: makefile` to manifest.yaml |

## 源码修改

- `common/pulseaudio-ctl.in`: Changed shebang from `#!/bin/bash` to `#!/usr/bin/env bash` for OpenHarmony portability

## 依赖版本

- coreutils 9.10 (precompiled package — provides `install`/`ginstall` command)
- bash (pre-installed at ~/usr/local/bin/bash and /data/service/hnp/bin/bash)
- make 4.4.1
- sed (GNU, via precompiled package)
- awk (gawk 5.4.0)

## 验证结果

```bash
$ head -1 ~/usr/local/bin/pulseaudio-ctl
#!/usr/bin/env bash

$ grep "^VERS=" ~/usr/local/bin/pulseaudio-ctl
VERS="1.70"

$ ~/usr/local/bin/pulseaudio-ctl 2>&1
I require pactl but it's not installed. Aborting.
```

Script runs correctly; exits gracefully when pactl is not available (expected on headless build server without PulseAudio).

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| pulseaudio-ctl-1.70-ohos-aarch64.tar.gz | 23KB | Release package (shell script + config + manpage + zsh completion) |
| pulseaudio-ctl-1.70-ohos-aarch64-debug.tar.gz | 23KB | Debug package (same content, no ELF binaries to separate) |

## 注意事项

- pulseaudio-ctl requires `pactl` and `pacmd` commands (PulseAudio utilities) at runtime — not available on headless OpenHarmony build server, but the script properly checks and exits gracefully
- This is a pure shell script project with no compiled binaries — no ELF signing, no strip, no RPATH needed
- The `make clean` target removes the manpage doc/pulseaudio-ctl.1 which is a pre-existing source file (Makefile has circular dependency for this target) — need to restore it from .orig if running clean before build
- Version 1.99 does not exist; the latest available version is 1.70 from graysky2/pulseaudio-ctl repository
---

**编译结束**: 2026-06-04 11:05
**最终状态**: published
