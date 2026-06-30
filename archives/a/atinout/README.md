# atinout

atinout 是一个 AT 命令工具，读取输入的 AT 命令发送到调制解调器（modem）并输出响应。

## 功能概述

- 从文件或标准输入读取 AT 命令
- 将 AT 命令逐行发送到 modem 设备
- 收集 modem 响应并输出到文件或标准输出
- 支持 `--version` 和 `--help` 命令行选项
- 单一源文件 (atinout.c)，编译产物为独立命令行工具

## OHOS 适配

- **Makefile CC 覆盖**：atinout 的 Makefile 使用 `CC = gcc`，在 OpenHarmony 上必须通过 `make CC=$CC` 覆盖为 clang
- **不能用 make -e**：使用 `make -e` 会导致环境 CFLAGS 覆盖 Makefile 的 CFLAGS（其中包含 `-DVERSION="0.9.1"` 定义），造成编译失败；应使用 `make CC="$CC"` 仅覆盖编译器
- **SourceForge URL 需要 filename 字段**：conandata.yml 中的 SourceForge 下载 URL 以 `/download` 结尾，Conan 无法自动识别为 tar.gz，需要在 conandata.yml 中添加 `filename: "atinout-0.9.1.tar.gz"` 字段
- **无 configure 脚本**：atinout 只有简单 Makefile，不是 autotools 项目，不需要 `./configure` 步骤
- **无测试套件**：Makefile 不包含 `check` 目标，无自带测试
- **未签名二进制限制**：OpenHarmony 平台上未签名二进制从某些目录执行会报 "Operation not permitted"，需复制到 $HOME 目录或通过 CI 签名流程

## 依赖关系

- **编译依赖**：无第三方依赖，仅需要 C 编译器 (clang)
- **运行依赖**：仅依赖 musl libc（系统自带）
- 无 Conan 包依赖

## 参考资料

- 官网：https://atinout.sourceforge.net/
- 源码下载：https://sourceforge.net/projects/atinout/files/
- 许可证：GPL-3.0
