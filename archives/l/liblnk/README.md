# liblnk

`liblnk` 是 libyal 项目提供的 C 语言库：Library to access the Windows Shortcut File (LNK) format。

## 功能概述

- 提供稳定的 C API、错误处理和对象生命周期管理；
- 读取并解析对应的 Windows 或磁盘镜像格式；
- 随包提供上游命令行工具；工具通过上游集成脚本验证。

## OHOS 适配

- 构建系统：Autotools，直接使用发布包自带的 `configure` 和 `Makefile.in`。
- 平台三元组：OHOS 下显式使用 `aarch64-unknown-linux-ohos`。
- `config.sub`：构建前补充 `ohos*` 和 `linux-ohos*` 平台识别，不修改上游测试断言。
- HMDFS：构建期统一 `umask 022`，并通过 `CONFIG_SHELL` 解释 configure 和测试 runner。
- libtool：测试执行时解析到 `.libs` 下的真实 ELF；不修改上游测试断言。

## 依赖关系

- 编译依赖：无外部 Conan 依赖。
- 发布包自带本地 libyal 组件：libbfio、libcdata、libcerror、libcfile、libclocale、libcnotify、libcpath、libcsplit、libcthreads、libfdatetime、libfguid、libfole、libfwps、libfwsi、libuna。
- 运行依赖：OHOS libc；未启用上游 Python 绑定。

## 参考资料

- 上游仓库：https://github.com/libyal/liblnk
- 当前配方版本：`20240423`
