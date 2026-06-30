# mcpp — C/C++ 预处理器

MCPP 是一个高质量的 C/C++ 预处理器，实现了 C90、C99 和 C++98 的全部预处理功能，具有最高的标准符合度。它可作为独立工具使用，也可嵌入其他程序作为子程序调用。

## 功能概述

- **完整预处理支持**: 实现 C90、C99、C++98 所有预处理指令和宏展开功能
- **验证套件**: 附带全面的 C/C++ 预处理器验证测试集
- **诊断信息**: 提供丰富且精确的预处理错误和警告诊断信息，可帮助排查源码中的潜在 bug 和可移植性问题
- **调试输出**: 支持多种 `#pragma` 指令输出调试信息
- **多字节编码**: 支持日文、中文、韩文等多字节字符编码（Shift_JIS、EUC-JP、Big5 等）
- **高可移植性**: 支持 UNIX 和 Windows 上多种编译器系统，可替代编译器内置预处理器
- **库模式**: 可作为子程序（`libmcpp`）嵌入其他主程序调用（需 `--enable-mcpp-lib` 编译选项）
- **行为可配置**: 可从源码生成不同行为规范的预处理器版本

## OHOS 适配要点

### 平台检测（E007）

mcpp 2.7.2 使用 2006 版的 `config.guess` 和 `config.sub`，不包含 HarmonyOS 检测分支。需要手动添加：

- `config.guess`: 在 case 语句中添加 `*:HarmonyOS:*:*` 分支，输出三元组 `aarch64-unknown-linux-ohos`
- `config.sub`: 在 `maybe_os` 列表和 OS 类型列表中添加 `linux-ohos*`

### 链接器兼容性（E064）

ohos-sdk 的 `lld` 链接器运行时依赖 libxml2.so.16，在当前环境中动态链接失败。解决方案：

- 使用 `clang-wrapper` 包装脚本，自动将 `-fuse-ld=bfd` 传递给 clang，使用 ld.bfd 替代 lld
- clang-wrapper 同时处理 conftest 二进制的 ELF 签名，绕过 configure 中"无法运行编译程序"的问题

### 临时目录权限（E011）

mcpp 的 `configure` 脚本使用 `umask 077` 创建临时目录，在 HMDFS 文件系统上会导致权限问题。需将两处 `umask 077` 改为 `umask 022`。

### 与 Linux 的差异

| 差异点 | Linux | OHOS | 说明 |
|--------|-------|------|------|
| 平台三元组 | aarch64-unknown-linux-gnu | aarch64-unknown-linux-ohos | config.guess/sub 需要补丁 |
| 链接器 | lld 正常工作 | lld 依赖 libxml2 失败 | 使用 ld.bfd 替代 |
| conftest 执行 | 可直接执行 | 需 ELF 签名 | clang-wrapper 处理签名 |
| 临时目录权限 | umask 077 正常 | HMDFS 下 umask 077 失败 | 改为 umask 022 |

## 依赖关系

### 编译依赖

无外部编译依赖。mcpp 是独立的 C 预处理器，仅需标准 C 编译器即可构建。

### 运行依赖

无运行依赖。mcpp 二进制不链接任何动态库。

## 已归档版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 2.7.2 | built | 2026-06-02 | 3 个平台适配补丁（config.guess/config.sub/configure） |

## 参考资料

- **官网**: https://mcpp.sourceforge.net/
- **源码仓库**: https://sourceforge.net/projects/mcpp/
- **许可证**: BSD-2-Clause（类似 BSD 许可证）
- **上游版本**: V.2.7.2 (2008/11)，最后一次上游发布