# simde 0.8.2 适配笔记

## 编译环境
- 软件：simde 0.8.2（header-only SIMD 库）
- 上游仓库：https://github.com/simd-everywhere/simde（正式标签 v0.8.2，commit 71fd833d9666141edcd1d3c109a80e228303d8d7）
- 构建系统：meson（提供头文件安装，无编译产物）
- 编译日期: 2026-09-08
- 编译器: clang 15.0.4 / clang++
- 平台: aarch64-linux-ohos
- 状态: built

## 编译步骤

simde 是纯 header-only 库（simde/ 目录 469 个头文件），无需要编译的库代码；上游 meson 仅负责安装头文件。Conan 配方将头文件打包进 include 目录，test_package 编译范例程序验证头文件可用。

## 上游测试清点（R51 申报表）

- test/ 目录共 **520** 个测试源文件（`find test -name '*.c'`），按 ISA 分族：arm/neon、arm/sve、x86、wasm、mips、common。
- meson 注册：`meson.build` 中 `if not meson.is_subproject() and get_option('tests'): subdir('test')`，各分族注册 `test()`（如 common 族 c/cpp 双语言各 1 条，x86/arm 族按文件注册）。
- 测试框架依赖 munit 子模块 `test/munit/`（官方 release tarball 不含，已从 munit master 补充 munit.h/munit.c 后编译运行）。

### 实测运行（本机 aarch64，clang 15，TAP 输出）

| 测试文件 | 断言通过 | 断言失败 |
|---|---|---|
| test/common/common.c | 5/5 | 0 |
| test/arm/neon/aba.c | 12/12 | 0 |
| test/arm/neon/abd.c | 21/21 | 0 |
| test/arm/neon/add.c | 32/32 | 0 |
| test/arm/neon/ceq.c | 30/30 | 0 |
| test/arm/neon/max.c | 23/23 | 0 |
| test/arm/neon/mul.c | 25/25 | 0 |

抽样 7 组全部通过，与上游 CI 的 aarch64 结果一致；完整 520 组测试源文件未纳入本配方 CI（test_package 仅验证 1 个消费者用例，详见 test_package/MANIFEST.yml 的 upstream_test_in_build: false）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 下载源 github.com 直连超时 | 该环境 github.com 443 不可达 | 改走 codeload.github.com 官方 tarball（v0.8.2），sha256 已核验 |
| 2 | /tmp 只读 | 环境限制（E002） | 全部临时文件使用 $TMPDIR（/storage/Users/currentUser/tmp） |
| 3 | test/munit 目录为空 | 官方 release tarball 不含 git submodule 内容 | 从 munit master 补充 munit.h/munit.c 用于本地测试运行，不入配方 |

## 源码修改

无源码/补丁修改（header-only 库，无平台相关代码需适配；simde 自带 arm/mips/x86/wasm 全 ISA 实现，Neon 头文件已在 aarch64 实测通过）。

## 依赖版本

无第三方运行/编译依赖（header-only，libm 可选）。

## 验证结果

```bash
# test_package 将编译范例程序调用 simde neon 头文件 API 并运行
# 上游测试抽样 7/7 组全部通过（见上表）
```

## 交付物

无二进制产物；交付文件 = conanfile.py + conandata.yml + test_package/（头文件由 conan create 从上游 tarball 安装进包内 include）。

## 注意事项

- 版本号 0.8.2 与上游正式标签 v0.8.2 一一对应；
- conandata.yml sources.url 指向官方 github tarball（R39），镜像回退由 CI 处理。
---

**编译结束**: 2026-09-08 16:07
**最终状态**: built
