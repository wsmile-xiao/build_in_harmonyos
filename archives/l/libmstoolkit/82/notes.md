# libmstoolkit 82 适配笔记

## 元信息

- 上游：`mhoopmann/mstoolkit`，tag `rev82`
- 源码 SHA256：`a306a5659c55d4f9290031c5820a4f28103cea8c130e9ed567b1f009d3cfc850`
- 许可证：Apache-2.0 AND BSD-2-Clause AND Artistic-1.0-Perl AND Zlib
  （按 19 个实际编译源文件及其引用的原始通知汇总）
- 构建系统：手写 Makefile；配方按其对象列表直接调用 profile 编译器

## 适配方案

上游 Makefile 固定使用 `g++`、`gcc` 和 `ar`，并把 Expat 2.2.0、SQLite
3.7.7.1、zlib 1.2.8 的源码直接编入静态库。配方保留 Makefile 中列出的 14 个
mzParser 源文件和 5 个 MSToolkit 源文件，但通过
`tools.build:compiler_executables` 取得交叉 `clang++`，并以 PATH 中的
`llvm-ar` 归档。第三方源码不参与编译，改用独立 Conan 包。

`0001-add-build-compatibility-header.patch` 新增仅用于构建的强制预包含头。它先引入
Expat 与 zlib 的公开头；两者与源码包内旧头使用相同 include guard，因此后续
`mzParser.h` 中的引号包含不会再让旧头生效。配方只在编译 `mzp_base64.cpp` 时关闭
Clang 的 C++17 `register` 诊断，不影响另外 18 个翻译单元。补丁只新增文件，
不改写上游 CRLF 文件，可由 Conan 和干净源码门禁一致重放。

## 依赖

- `expat/2.8.2.1.1`
- `sqlite3/3.49.1`
- `zlib/1.3.2`

三个依赖均已在 `ohpcd` 远端通过配方下载预检。完整 MSToolkit 构建保留 SQLite
支持，没有使用 `_NOSQLITE` 缩减功能。

## 上游测试清点

`rev82` 源码包没有 `tests/` 或 `test/` 目录，不包含 CTest、GoogleTest、pytest
等测试注册；顶层 Makefile 只有 `all`、`lite`、`clean` 及对象编译规则，没有
`test`/`check` 目标。因此上游测试口径为 0 个，配方输出
`HMBS_UPSTREAM_TEST_RESULT` 的 `status=no_tests, discovered=0, executed=0`。

## 新增验证

- 通用消费者测试：调用公开 `Spectrum`、`MSObject`、`MSReader` API，把两条峰写成
  MS2 文件后读回并核对扫描号、峰数量、m/z 与强度。
- HarmonyOS 专项测试：以 `#ifndef __OHOS__` 和非 AArch64 `#error` 方式 fail
  closed，在 `$TMPDIR` 中执行独立 MS2 文件回环，并验证实际文件权限与数据。
- 测试程序通过 Conan 生成的 `libmstoolkit::libmstoolkit` 目标消费安装后的头文件、
  静态库及传递依赖，不引用源码目录。

## 当前验证状态

- 官方源码 SHA256、补丁重放、19 个源文件的本机 Clang C++17 编译、静态归档及通用
  MS2 回环测试已通过。
- OHOS profile 的依赖图解析及三个依赖的远端二进制命中已通过。
- 当前 macOS 主机没有 `/data/service/hnp/bin/clang++`，HarmonyOS PC/AArch64
  `conan create` 对 profile 显式配置但不可用的编译器立即 fail closed；因此归档保持 `failed`，
  不声明 `built`，也不生成 `.ci-result.json`。

## 产物

- `lib/libmstoolkit.a`
- `include/` 下 9 个公开 MSToolkit/mzParser 头文件
- `res/upstream_test_result.json`（供缓存命中时复发上游零测试证据）
- `licenses/` 中包含 Apache-2.0、BSD-2-Clause 标准全文，以及 Artistic、Zlib
  对应的上游原始完整条款/通知和逐文件版权通知

## 注意事项

- `MSReader.h` 在非 MSVC 平台要求 `_LARGEFILE_SOURCE`，配方将该宏以及
  `_FILE_OFFSET_BITS=64` 作为消费者定义传播。
- 源码目录中的旧版 Expat、SQLite、zlib 头文件不得先于 Conan 依赖头文件进入
  include 搜索路径，否则会产生版本错配。
---

**编译结束**: 2026-09-15 00:14
**最终状态**: failed
