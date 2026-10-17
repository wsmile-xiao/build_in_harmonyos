# colibri-core 2.5.9 HarmonyOS 适配笔记

## 适配范围

本配方迁移上游 C++ 核心、`libcolibricore.a`、7 个原生 C++ 命令以及 10 个 Bash 组合分析命令。上游仓库附带的 Python/Cython 绑定不属于本次明确指定的 C++ 库范围。

## 依赖和构建

- 构建系统：Autotools，源码归档需要先运行 `autoreconf -fiv`。
- 目标：HarmonyOS 6.0、aarch64、Clang 15、libc++。
- 依赖：`bzip2/1.0.8`。
- 构建参数：`--enable-static --disable-shared`。
- 构建工具通过 Conan `tool_requires` 提供，避免依赖 worker 的隐式系统环境。

## 上游测试清点（R51）

- Automake 注册测试套件：1 个，`src/tst.sh`。
- 实际测试程序：`src/colibri-test`。
- 实测断言：1007 个，覆盖类编解码、n-gram/skipgram/flexgram、序列化、模式模型、反向索引和对齐模型。
- 配方在 `build()` 阶段执行 `make check`；任何断言失败都会终止 `conan create`。

## 适配修改

1. 移除 `PatternPointer` 中冗余的 `operator Pattern()`；Clang 会将其诊断并执行为无限递归，而原有 `Pattern(const PatternPointer&)` 转换构造函数已完整保留相同转换能力。
2. 六个 CLI 将 `getopt()`/`getopt_long()` 返回值从 `char` 改为 `int`。该 API 使用 `-1` 表示选项结束，而 aarch64 上默认无符号 `char` 会把 `-1` 转成 255，导致错误的 `Unknown option: -0`。
3. `src/test.cpp` 先进入 `TMPDIR`，随后使用相对临时文件名。测试内容和 1007 个断言均未删除或跳过。
4. 十个已安装脚本将 `/bin/bash` shebang 改为 `/usr/bin/env bash`，由 HarmonyOS 工具环境从 PATH 解析 Bash。
5. `autoreconf` 后对生成的 `configure`/`config.guess` 将 `umask 077` 调整为 `umask 022`，避免 HMFS/HMDFS 对 0700 临时目录的权限调解导致配置失败。
6. 生成的 `config.guess` 增加 HarmonyOS/HongMeng 原生识别，并用 `config.sub aarch64-unknown-linux-ohos` 验证标准三元组；不通过 `--build` 绕过原生平台探测。
7. HarmonyOS 原生构建继续优先使用 Conan 提供的 Autotools，但 `autoreconf` 显式改用系统原生 Perl，并将 `PERL5LIB` 限定为 Conan Automake 的纯 Perl 模块目录，避免 HMFS 拒绝加载 Conan Perl 的 `Cwd.so`。
8. `ACLOCAL_PATH` 显式包含 Conan `libtool`、`pkgconf` 和 `autoconf-archive` 的宏目录，确保 `LT_INIT`、`PKG_PROG_PKG_CONFIG` 及 `AX_*` 宏在原生 Worker 上展开，不依赖系统 `/usr/share/aclocal`。由于 `libtool/2.5.4` 的 `libtoolize` 内嵌不可重定位前缀，配方先从该 Conan 包复制 m4 宏和 `ltmain.sh`，再仅跳过 `libtoolize` 子步骤，其余 `autoreconf` 流程保持完整执行。

## 验证

- 官方源码 SHA-256 校验通过。
- 上游测试：1007/1007。
- 消费者测试：6/6，真实链接并调用 Colibri Core API，同时执行原生命令和 Bash 命令。
- 安装产物：1 个静态库、11 个公开头文件、7 个原生命令、10 个脚本命令和 pkg-config 元数据。

## 最终状态

HarmonyOS AArch64 构建、上游测试、消费者测试、命令验证及赛事质量门均全部通过。
