# DRAFT-PLAYERCTL-2.4.1-MESON-HELPER-SHEBANG-RUN-REWRITE: conan Meson helper 在 OHOS 下的 shebang 死角与 run() 改写

- **草稿 ID**: DRAFT-PLAYERCTL-2.4.1-MESON-HELPER-SHEBANG-RUN-REWRITE
- **严重度**: 2
- **类别**: conan, ohos, meson, shebang, build-system
- **来源**: playerctl 2.4.1 适配（HarmonyOS PC aarch64）；E232（autotools 版）的 meson 侧泛化

## 错误特征

```
/system/bin/sh: /storage/Users/currentUser/.conan2/p/meson*/bin/meson: Permission denied
ConanException: Error 126 while executing
```

（附带：`AttributeError: 'Meson' object has no attribute 'compile'` —— Meson helper
方法集为 configure()/build()/install()，不存在 compile()。）

## 根因分析

conan 的 Meson helper（`conan/tools/meson/meson.py`）把命令硬编码为裸名 `meson <args>`，
且无官方挂钩。meson 包的 `bin/meson` 是 `#!/bin/sh` 脚本；OHOS 沙箱的 `execve()` 不接受
system shell 作 shebang 解释器——实测 `#!/bin/sh`、`#!/data/service/hnp/bin/bash`、
`#!/system/bin/sh` 全部 EACCES（errno=13 而非 8），唯一可用的 shebang 解释器是 conan
侧 python3。

## 推荐方案

**方法**: recipe-run-rewrite-python-meson

在配方中覆写 `run()`：仅当 `settings.os == "OHOS"` 且命令以 `meson ` 开头时，把
`meson <args>` 改写为 `<python 绝对路径> <meson 包 site-packages>/mesonbuild/core.py
<args>`。不修改 conan 框架与 meson 包本体。实测配置/编译/安装全部通过，exit=0。

## 禁止事项

- 修改 meson 包 `bin/meson` 的 shebang 或 conan 框架 helper 源码（框架/依赖文件，协作者不可改）
- 用 chmod 试图修复 shebang（execve 语义问题，chmod 无效）
