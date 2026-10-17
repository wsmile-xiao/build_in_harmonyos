# belr 5.3.105 适配笔记

## 概览

- 软件：belr 5.3.105（Belledonne Communications 的 ABNF 语法识别 / 解析库）
- 类型：C++ 库（静态包，`libbelr.a` + `include/belr/*.h`）
- 依赖：bctoolbox/5.3.115（运行时）；bcunit/5.3.113（测试框架，test_requires）
- 构建系统：CMake（上游自带 CMakeLists，测试为 bcunit 框架的 `tester/belr-tester`）
- 目标平台：HarmonyOS PC（aarch64-linux-ohos，clang 15.0.4 / libc++ / CMake 4.1.2 / Conan 2.29.1）
- 适配路径：路径 A（基础适配，无补丁）
- 状态: built

## 编译环境

```bash
conan create archives/b/belr/5.3.105 \
  -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64
```

配方流程：

1. `source()` 解包上游 `5.3.105` 官方 tarball（sha256 校验）。
2. `generate()`：`ENABLE_STRICT=OFF`、`ENABLE_UNIT_TESTS=ON`、`ENABLE_TOOLS=OFF`、
   `BUILD_SHARED_LIBS=OFF`，并用 `BCToolbox_DIR` 指向上游 `BCToolboxConfig.cmake`
   （它提供 `BCToolbox_TARGET` 与 `bc_apply_compile_flags()`，Conan 生成的
   config 不提供这两个）；OHOS 上按 E092 固定 `CMAKE_SYSTEM_NAME=Linux`。
3. `build()`：配置编译后**直接执行** `tester/belr-tester`（bcunit 框架，
   Grammar 3 例 + Parser 2 例），上游未把 tester 注册进 ctest。
4. `package()`：安装库与头文件、LICENSE；移除 `bin/`（tester 是构建期验证产物，
   与 bctoolbox/5.3.115 同款处理）；并把 belr 公共头依赖的 bctoolbox 头文件
   一并安装（原因见下）。
5. `test_package/`：消费者视角用例（9 个断言）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 消费者编译报 `bctoolbox/defs.h not found` | Belledonne 包的 CMakeDeps 配置不向**间接**消费者导出 include 目录：实测 `bctoolbox_INCLUDE_DIRS_RELEASE` 为空；用 `bzrtp/5.3.105` 做间接依赖复现同样为空 | 与仓库既有 `bzrtp/5.3.105` 同款处理：`package()` 把 belr 公共头依赖的 `bctoolbox/*.h/.hh` 安装进本包 `include/bctoolbox/`，`package_info()` 仍以 `bctoolbox::bctoolbox` 作为链接需求 |
| 2 | `find_package(BCToolbox)` 后 `bc_apply_compile_flags` 未定义 | Conan 生成的 `BCToolbox` config 不含上游的 `BCToolboxCMakeUtils.cmake` | 用 `BCToolbox_DIR` 指向 bctoolbox 包内上游 config（`share/BCToolbox/cmake`），由它加载上游宏 |
| 3 | 上游 tester 未注册 ctest | `tester/CMakeLists.txt` 只有 `add_executable`，没有 `enable_testing/add_test` | `build()` 直接运行 `tester/belr-tester`；资源目录由 `config.h` 的 `BELR_LOCAL_RESOURCE_LOCATION` 指到源码 `tester/res`，`cwd=build_folder` 即可 |
| 4 | handler 用裸函数指针编译失败（`ParserHandler` 需要 `_createElementFn::result_type`） | belr handler 类型要求 `std::function` | 用 `make_fn(nullptr)` 包装，或直接传 `std::function<shared_ptr<T>(const string&, const string&)>` |

## 平台差异说明

- 上游源码、构建文件与测试用例零改动（`patches_applied: []`），全部 5 个上游用例原样通过。
- 上游 CLI 工具（`belr-parse` / `belr-compiler`）不在本包交付范围：本仓库要求 CLI 包提供软件级
  `commands.json`（R38），而版本目录 PR 只能改动 `<包>/<版本>/`（PF9），故按纯库包交付，
  `ENABLE_TOOLS=OFF`；需要工具时可基于上游源码自行构建。

## 验证结果

```text
上游测试（build() 内直接执行 tester/belr-tester）:
  Suite [Grammar]: 3/3 passed（SIP grammar save and load / aliases rules / Grammar loader）
  Suite [Parser] : 2/2 passed（Parser connected to C functions / Parser with inheritance）
  → 5/5 通过

消费者测试（test_package）: BELR_CONSUMER_CHECKS=9 FAILURES=0 → BELR_CONSUMER_OK
```

## 交付物

| 文件 | 说明 |
|------|------|
| lib/libbelr.a | 静态库 |
| include/belr/*.h | 公共头（abnf.h、belr.h、grammarbuilder.h、parser.h） |
| include/bctoolbox/** | belr 公共头依赖的 bctoolbox 头文件（见问题 1） |
| share/Belr/cmake/* | 上游 CMake config（BelrConfig.cmake 等） |
| licenses/LICENSE.txt | GPL-3.0-or-later |

## 依赖链上下文

本包是 `belle-sip` 的前置依赖（belle-sip `CMakeLists.txt` 中
`find_package(Belr 5.3.0 REQUIRED)`），而 belle-sip 又是 `lime` 上游测试器的前置依赖。
因此 belr 按依赖项优先适配并提交。

## 编译结束

- 目标：在鸿蒙 PC 上完成 belr 5.3.105 适配并跑通上游测试。
- 结论：上游 bcunit 套件 5/5 通过、消费者用例 9/9 通过，零补丁。

### 对话 #1

- 会话：Codex（Lee-BX / 南京大学 PT）
- 过程：init-build → 配方（BCToolbox/BCUnit 集成）→ `conan create` 迭代 4 轮 →
  上游 tester 5/5 + 消费者 9/9 → 提交 PR。
- 关键修正：BCToolbox 上游 config 注入、bctoolbox 头文件随包、handler 必须用
  `std::function`/`make_fn`。
---

**编译结束**: 2026-10-01 22:57
**最终状态**: built
