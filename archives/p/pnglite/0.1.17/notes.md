# pnglite 0.1.17 适配笔记

## 编译环境

- 构建系统：配方侧最小 CMake（上游发布包无构建文件）
- 编译日期：2026-09-15
- 编译器：OHOS Clang 15.0.4，目标为 HarmonyOS/OpenHarmony AArch64
- 状态：built

## 上游测试清点

| 清点项 | 数量 | 证据 |
|--------|------|------|
| 发布包普通文件 | 2 | `pnglite.c`、`pnglite.h` |
| tests/test 目录 | 0 | 三层目录清点无匹配目录 |
| 测试/示例源文件 | 0 | 未发现 `main()`、assert 或测试框架引用 |
| 构建/测试入口 | 0 | 无 Makefile、CMakeLists.txt、configure、meson.build |
| 上游可执行测试 | 0 | 官方 zip 没有测试命令或已注册测试 |

上游实测口径为 0/0；不存在被跳过、删减或修改的上游测试。适配后新增两个消费者可执行测试，共 25 个断言。

## 编译步骤

1. 从 SourceForge 官方 0.1.17 发布页下载 zip，并用 SHA-256 校验。
2. 应用 `refresh-patch --auto` 生成的源码补丁。
3. 通过 Conan `zlib/1.3.1` 依赖生成 CMake 配置，使用 OHOS 工具链编译 `libpnglite.a`。
4. 构建并执行 API 编解码往返测试与 HarmonyOS `__OHOS__`/AArch64 专项测试。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `../zlib/zlib.h` 无法解析 | 上游假设 zlib 与 pnglite 源码目录相邻 | 改用依赖公开头 `<zlib.h>` |
| 2 | PNG 写入路径发生堆越界 | IDAT 缓冲区按未压缩大小分配，没有使用 zlib 上界 | 使用 `compressBound()` 分配并检查分配、压缩返回值 |
| 3 | PNG 大端字段解析触发 UBSan | 字节提升为有符号 `int` 后左移 24 位 | 左移前显式转换为 `unsigned` |
| 4 | 单独包含 `pnglite.h` 时 `size_t` 未声明 | 公共头未包含定义 `size_t` 的标准头 | 在公共头中包含 `<stddef.h>` |
| 5 | zlib 静态对象无法链接进共享库 | 已发布 zlib 包为静态且对象不是 PIC | pnglite 交付为静态库，并显式传播 zlib 依赖 |

## 源码修改

- `0001-pnglite.c.patch`：标准化 zlib 头引用，修复大端字段未定义行为及 IDAT 压缩缓冲区越界。
- `0002-pnglite.h.patch`：让公开头自包含。
- 官方源码使用 CRLF；配方解压后用 Conan 文件工具规范化为 LF，再应用仓库标准 LF 补丁。

## 依赖版本

- zlib/1.3.1

## 验证结果

- 官方上游测试：0/0（发布包确无测试）
- API 消费者测试：1/1 通过，20/20 断言通过
- HarmonyOS 特有测试：1/1 通过，5/5 断言通过
- 合计：2/2 测试通过，25/25 断言通过

## 交付物

- `lib/libpnglite.a`
- `include/pnglite.h`

## 注意事项

- 支持上游原有的非交错、8/16 位 PNG 能力；索引色和交错 PNG 仍按上游行为返回 `PNG_NOT_SUPPORTED`。
- 本包没有命令行工具，因此不提供 `commands.json`。
---

**编译结束**: 2026-09-15 02:25
**最终状态**: built
