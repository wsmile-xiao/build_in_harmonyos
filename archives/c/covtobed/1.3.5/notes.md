# covtobed 1.3.5 适配笔记

## 编译环境

- 目标环境：HarmonyOS PC / OHOS 6.0 / aarch64
- 构建系统：custom（上游 1.3.5 未提供 Makefile、CMakeLists.txt 或 configure）
- 编译器：Conan profile 中 `tools.build:compiler_executables.cpp` 指定的 clang++
- C++ 标准：C++11
- 编译日期：2026-09-09

## 编译步骤

配方下载上游 `v1.3.5` 标签源码，直接编译 `base.cpp` 和
`OptionParser.cpp`。头文件路径、静态库路径和库名全部从 Conan 依赖元数据
生成，不读取系统 `/usr/include` 或 `/usr/lib`。链接顺序保持目标文件在前、
`bamtools` 和 `zlib` 静态库在后，以兼容 OHOS 的 ELF 链接器。

生成 `covtobed` 后，配方在源码根目录显式调用 `bash test/test.sh`，最后只把
新编译的可执行文件和 MIT 许可证装入 Conan 包。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游没有构建系统文件 | 官方 CI 直接调用 g++ 编译两个翻译单元 | 在 Conan `build()` 中使用 profile 注入的 clang++ 直接编译 |
| 2 | 上游测试脚本最后一项调用 Perl | OHOS 基础环境不能假设自带 Perl | OHOS 构建以 `perl/5.42.2` 作为 `tool_requires` 并生成 VirtualBuildEnv |
| 3 | 发布源码内含旧的预编译 `covtobed` | 上游归档同时携带 Linux/macOS 二进制 | 构建命令覆盖源码根目录的同名文件，测试和打包均只使用本次生成的程序 |
| 4 | 本机重建 zlib 时默认寻找 `/data/service/hnp/bin/bash` | 依赖配方面向 OHOS worker | 本机验证显式设置 `CONFIG_SHELL=/bin/bash`；OHOS profile 保持 worker 路径 |

## 源码修改

无需补丁。适配仅新增 Conan 配方、测试包和归档元数据。

## 依赖版本

- `bamtools/2.5.3`：运行/链接依赖，OHOS aarch64 静态包已在 ohpcd 仓库核验
- `zlib/1.3.1.1`：运行/链接依赖，OHOS aarch64 静态包已在 ohpcd 仓库核验
- `perl/5.42.2`：仅运行上游测试，OHOS aarch64 工具包已在 ohpcd 仓库核验

## 验证结果

- 使用项目的 OHOS 6.0 aarch64 profile 解析依赖图成功，三个依赖均命中已发布二进制包。
- macOS arm64 上使用同一配方执行干净 `conan create` 成功。
- 上游 `test/test.sh`：14/14 个独立检查通过。
- `test_package`：版本、帮助文本、官方 mock BAM 精确 BED 输出共 3/3 通过。
- 总计：17/17 断言通过。

本机没有 OHOS SDK 和 OHOS 可执行环境，因此上述执行结果是配方的原生预验证；
目标平台构建与运行由仓库 W3/远端 CI 复现，不能把 macOS 结果冒充为 OHOS 真机结果。

## 交付物

| 文件 | 说明 |
|------|------|
| `bin/covtobed` | Conan 应用包中的命令行程序 |
| `licenses/LICENSE` | 上游 MIT 许可证 |
---

**编译结束**: 2026-09-09 03:29
**最终状态**: built
