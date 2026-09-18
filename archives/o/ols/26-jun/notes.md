# ols 26-jun 适配笔记

## 编译环境
- 构建系统: odin build (Odin 语言项目，无 cmake/autotools)
- 编译日期: 2026-09-13
- 编译器: clang (OHOS: /data/service/hnp/bin/clang)
- Odin 编译器: dev-2026-08-nightly (静态链接，aarch64 ELF)
- 状态: built（待真机预检确认）

## 架构说明

ols 是用 Odin 语言编写的 LSP 服务器，依赖 Odin 编译器进行构建。
OHOS 生态中尚无 Odin 编译器 Conan 包，因此本配方：
1. 从 GitHub Release 下载 ols dev-2026-08 源码
2. 同时下载匹配的 Odin dev-2026-08 aarch64 预编译二进制（静态链接 ELF，无需外部 libc）
3. 使用 Odin 编译器 + OHOS clang 从源码编译 ols 和 odinfmt
4. 在 build() 阶段运行上游测试套件（`odin test`）

OHOS 设备上 Odin 静态二进制可直接运行（无外部依赖），clang 链接生成 musl-compatible ELF。

## 编译步骤

```bash
# 1. 下载源码和 Odin
get(conandata, "ols-source")    # ols dev-2026-08 源码
get(conandata, "odin-arm64")    # Odin dev-2026-08 aarch64 静态二进制

# 2. 构建 ols
odin build src/ \
    -collection:src=src \
    -out:ols \
    -no-bounds-check \
    -o:speed \
    -define:VERSION=26-jun

# 3. 构建 odinfmt
odin build tools/odinfmt/main.odin \
    -file \
    -collection:src=src \
    -out:odinfmt \
    -no-bounds-check \
    -o:speed

# 4. 运行上游测试 (893 tests)
cd tests/
odin test ../tests \
    -collection:src=../src \
    -define:ODIN_TEST_THREADS=1 \
    -define:ODIN_TEST_TRACK_MEMORY=false

# 5. 运行 odinfmt 快照测试
odin run tests.odin -file -collection:src=../../src -out:odinfmt_tests.exe
./odinfmt_tests.exe
```

## 上游测试结果（本地实测，Odin dev-2026-08 + ols dev-2026-08 完全匹配）

```
Finished 893 tests in 582ms. All tests were successful.
odinfmt snapshot tests: all passed
```

**未通过用例：无**（893/893 通过）

注意：当使用 Odin dev-2026-07 时，有 1 个测试失败（`ast_hover_type_specialization`，
属 Odin API 变更导致的版本不匹配问题，非平台问题）。使用匹配的 dev-2026-08 后全部通过。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | ols 预编译二进制为 glibc 链接，OHOS 使用 musl | 官方 release 仅提供 glibc 预编译版 | 改为从源码构建，链接 OHOS musl libc |
| 2 | Odin dev-2026-09 与 ols dev-2026-08 源码 API 不匹配 | `Inline_Asm_Expr` 从 AST 移除 | 使用匹配的 Odin dev-2026-08 |
| 3 | 上游测试需要 Odin 编译器 | 测试使用 `@(test)` 装饰器 | 内嵌 Odin 编译器到配方 |
| 4 | ols 运行时寻找 `odin` 二进制 | ols 的 `odin_command` 配置项 | test_package 仅测试 LSP 握手，不涉及 checker |

## 源码修改

无源码修改。仅使用官方源码，无 patch。

## 依赖

- 无 Conan 运行时依赖
- Odin 编译器通过 conandata.yml 内嵌下载（非 Conan 依赖）
- 链接依赖：OHOS musl libc（系统提供）

## 验证结果

```bash
# 本地 x86_64 验证（Odin dev-2026-08 + clang 替代品）
export PATH=".../odin-linux-amd64-nightly+2026-08-06:$PATH"
odin build src/ -collection:src=src -out:ols -no-bounds-check -o:speed -define:VERSION=test
odin test ../tests -collection:src=../src -define:ODIN_TEST_THREADS=1
# 输出: Finished 893 tests. All tests were successful.

# OHOS 真机验证（待设备恢复后）
ssh ohos@c1.sermc.net 'conan create archives/o/ols/26-jun -pr=ohos-aarch64'
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| bin/ols | ~2.2 MB | Odin Language Server (OHOS aarch64 musl ELF) |
| bin/odinfmt | ~960 KB | Odin 代码格式化器 |
| builtin/ | 3.3 KB | 内置类型定义（builtin.odin + intrinsics.odin）|
| licenses/LICENSE | 1.1 KB | MIT License |

## 注意事项

- ols 在 OHOS 上运行需要 ELF 代码签名（recipe 的 `_sign_ohos` 在 package() 阶段自动完成）
- 上游测试套件（893 个用例）已在 build() 中集成执行
- test_package 使用 LSP JSON-RPC 协议做冒烟测试（实质调用被测包 API，符合 R34）
- OLS_BUILTIN_FOLDER 环境变量指向 builtin/ 目录，供 ols 运行时查找核心类型定义

---

**编译结束**: 2026-09-13
**最终状态**: 待真机预检
