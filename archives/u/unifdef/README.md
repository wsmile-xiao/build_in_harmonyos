# unifdef

`unifdef` 选择性移除 C 源文件中的预处理器条件编译指令（`#if` / `#ifdef` / `#ifndef` / `#elif` / `#else` / `#endif`）：删除指令本身，以及其判定为“不保留”的整段文本，其余内容原样保留。常用于剥离重度 `#ifdef` 的平台差异代码、生成干净的导出头文件（Linux 内核 headers_install 即使用 unifdef），或作为轻量预处理器使用。

上游 [dotat.at/prog/unifdef](https://dotat.at/prog/unifdef/)（作者 Tony Finch，BSD-2-Clause）。

## 功能概述

- `unifdef` — 主程序（单文件 C）：按 `-D`/`-U` 等参数解析条件编译并输出裁剪后的源码，支持原地修改（`-m`）、带备份修改（`-M~`）、控制符号列举（`-s`/`-S`）、退出码模式（`-x`）等
- `unifdefall` — 包装脚本：先枚举文件中全部控制宏，再调用 unifdef 处理所有条件编译
- 退出码有语义：`0`=输出与输入一致，`1`=输出有变化，`2`=错误

## 依赖关系

- 编译依赖：无（ANSI C + POSIX shell，仅链接系统 libc）
- 运行依赖：`unifdef` 无；`unifdefall` 需要宿主提供可用的 C 预处理器（`cc -E`）与 `sort`/`sed`

## OHOS 适配要点

- 上游 POSIX Makefile 未经修改即可用 OHOS SDK clang（aarch64-linux-ohos）交叉编译，零补丁、无平台宏
- 上游 `make install` 依赖 `install(1)` 并在 man 目录建软链接；本配方 `package()` 改为直接 copy 产物（`bin/unifdef`、`bin/unifdefall`、man 手册）
- 上游 90 例 shell 回归全部保留执行：设备/CI 上 82/90 通过；8 例失败源于宿主环境差异（非 unifdef 缺陷），逐项原因见 [2.12/notes.md](2.12/notes.md) 与 [2.12/test_package/MANIFEST.yml](2.12/test_package/MANIFEST.yml)
- `unifdefall` 在无 C 预处理器环境（如未配置 sysroot 的交叉工具链）下功能受限，主程序不受影响

## 参考资料

- 官网与下载：<https://dotat.at/prog/unifdef/>
- 手册（man）：`share/man/man1/unifdef.1`
- 协作仓库：<https://github.com/fanf2/unifdef>

## 版本

- `2.12` — 适配 HarmonyOS PC（aarch64-linux-ohos / armv8），零补丁；见 [2.12/notes.md](2.12/notes.md)

## 产物

| 路径 | 说明 |
|------|------|
| `bin/unifdef` | 主程序（arm64 ELF） |
| `bin/unifdefall` | 包装脚本 |
| `share/man/man1/unifdef.1`、`unifdefall.1` | man 手册 |
