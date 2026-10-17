# cfm

Cactus File Manager (cfm) — 简洁快速的 TUI 文件管理器，纯 C 单文件实现，
无任何外部依赖（仅 POSIX libc/termios）。

## OHOS 适配

- 官方 tag v0.6.6 源码（github.com/sophec/cfm）直接编译，无需补丁。
- 构建系统：纯 Makefile（无 configure），`make` 即可产出 `cfm` 可执行文件。
- 适配要点：HarmonyOS 环境缺少 GNU `install` 命令（知识 E108/E182），
  配方 package() 直接用 `copy()` 拷贝 `cfm` 与 `cfm.1`，绕开 `make install`。
- 消费者验证：安装后以 pty 驱动 `cfm <dir>`，验证 TUI 渲染（转义序列）与
  `q` 干净退出（exit 0）。

## 功能

- Vi 风格按键的文件管理：导航、复制、移动、删除（含撤销）、标记、多视图。
- `$EDITOR`/`$SHELL`/`$OPENER`（或 `$CFM_*` 前缀）外部工具集成。

## 依赖

- 无运行时依赖（纯 libc/POSIX）。

## 参考

- 官网: https://github.com/sophec/cfm
