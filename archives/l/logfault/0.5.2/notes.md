# logfault 0.5.2 适配笔记

## 库简介

logfault（jgaa/logfault）——header-only 单头文件 C++ 应用日志库，交付物只有
`include/logfault/logfault.h`（501 行，含 MIT 许可证头）+ `LICENSE`。提供
`LFLOG_ERROR/WARN/NOTICE/INFO/DEBUG/TRACE` 六级流式日志宏、`LFLOG_IFALL_*` 条件宏（`LOGFAULT_ENABLE_ALL`
门控）、StreamHandler/ProxyHandler 等日志目标、LogManager 级别控制。纯标准库，
零运行依赖、无编译产物（README 自述 "No dependencies, except the standard-library"）。

## 编译环境

- 构建系统: header-only（`package_type = "header-library"` + `implements = ["auto_header_only_mode"]`；上游测试面为 CMake + gtest）
- 编译日期: 2026-09-27
- 编译器: clang 15 / clang++（OHOS SDK，aarch64-unknown-linux-ohos / libc++）
- 状态: built（conan-verify + W3 通过，未 upload）

## 编译步骤

本包无编译交付物；`conan create` 的三个执行面：

1. **`build()` = 上游测试集成（R51）**：`apply_conandata_patches`（0001 补丁）→
   `cmake.configure(LOGFAULT_BUILD_TESTS=ON)`（CMakeDeps/CMakeToolchain，GTest 由
   `test_requires("gtest/1.17.0")` 提供）→ `tools.build:jobs=2`（OHOS 下钉住，防
   `-j20` fork 耗尽，先例 erkir/openjpeg2）→ `cmake.build()` →
   `ctest --output-on-failure -V`（两个 gtest 可执行的 `[ PASSED ]` 汇总行打进
   G2/W3 日志；任一失败即构建失败）。
2. **`package()`**：`copy *.h (include/) → include/`、`copy LICENSE → licenses/`。
3. **`test_package`**：CMake 消费者 `test_logfault.cpp`，`find_package(logfault)` 后
   include 交付头真实调用 API，18 条运行期 check 逐条打印读数，`test()` 以
   `self.run(<bin>, env="conanrun")` 真跑（L0d）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `gtest-port.h:273: error: C++ versions less than C++17 are not supported`，两个测试目标编译失败 | 本制品仓仅提供 gtest/1.17.0（硬性要求 C++17），上游 `tests/CMakeLists.txt` 给测试目标钉 `CXX_STANDARD 14`（其 conanfile 锁 gtest/1.14.0 支持 C++14，该版本不在 ohpcd registry） | 补丁 `0001-tests-cxx-standard-17.patch`：两个测试目标 CXX_STANDARD 14→17；只改标准档位，测试用例与断言零改动 |
| 2 | init-build 对 BUILD_SYSTEM 猜成 autotools、conanfile/test_package 模板全部缺位（`模板不可用，跳过`） | registry 无 logfault 条目（全新包），模板回退链猜错 | 手写 header-only 配方（参照 crcpp/1.2.1.0 先例），manifest/notes 手工补齐 |
| 3 | 消费者测试编译报 `no member named 'clog' in namespace 'std'` | logfault.h 只前置声明 ostream 面、不 include `<iostream>`；`std::clog` 定义在 `<iostream>` | 消费者测试补 `#include <iostream>`（上游测试源同法但其经 gtest 链路带入了 iostream） |
| 4 | conan 默认 `-j<tools.build:jobs>` 取 `os.cpu_count()`=20，affinity 只有 8 | Conan CMake helper 无条件追加 `-j20`（§一.7 2.5× 超订）；CI 内存窗口下会 fork 耗尽被报成编译失败 | `build()` 内 `if str(self.settings.os) == "OHOS": self.conf.define("tools.build:jobs", 2)`（先例 erkir CI #62527 实测） |
| 5 | `default_to_clog_with_tid` 的 `HelloTid` 只在 `#if defined(__linux__) && defined(LOGFAULT_USE_TID_AS_NAME)` 注册 | OHOS clang triplet 为 aarch64-unknown-linux-ohos，`__linux__` 有定义 | 计数按框架注册实测（5+6=11）而非源码宏（7），差额逐项归因（见 test-report.md） |

## 源码修改

补丁 `patches/0001-tests-cxx-standard-17.patch`（`patches_applied` 同步）：
`tests/CMakeLists.txt` 两个 `set_property(TARGET ... PROPERTY CXX_STANDARD 14)` →
`17`。不触碰任何测试用例、断言或测试逻辑；交付头与其余源文件零改动。

## 依赖版本

- 运行交付依赖：**0**（header-only 纯标准库；W0 实核无外部 `find_package`）
- 测试期依赖（不进交付）：`gtest/1.17.0`（`conan list -r=ohpcd` 实查在档，
  armv8/OHOS/clang15/libc++/Release 二进制可得）

## 验证结果

```bash
# 上游测试（沙箱 HOME 字面执行，取数命令见 reports/test-report.md）
HOME="$TASK_DIR/test-home" ctest --test-dir "$TASK_DIR/sandbox/build" --output-on-failure -V
  1: [==========] 5 tests from 1 test suite ran.
  1: [  PASSED  ] 5 tests.
  2: [==========] 6 tests from 1 test suite ran.
  2: [  PASSED  ] 6 tests.
  100% tests passed, 0 tests failed out of 2

# 消费者测试（沙箱 HOME 字面执行，对已安装包 include/ 编译）
HOME="$TASK_DIR/test-home" ./test_logfault
  [consumer] summary: 18/18 checks passed (runtime), compile-time static_assert=1
  沙箱 HOME 回读 = 0 个条目（未向真实 HOME 写入）

# 交付件指纹
sha256(<pkg>/include/logfault/logfault.h) == sha256(<源码>/include/logfault/logfault.h)
  = 5affdb99d11f024ef57027f10be7f98ab0ebbd03d19cc614ae20f7805145d24d
```

计数口径（四口径分列，不混用；N=候选数法最大值）：

| 口径 | 数值 | 归属 |
|------|------|------|
| 源码宏数（次口径） | 7（tests/default_to_clog.cpp 内 7 个 `TEST(` 位：5 无条件 + linux/win32 门控 HelloTid 各 1） | 说明列 |
| 框架注册数（申报 N） | 11（default_to_clog=5 + default_to_clog_with_tid=6） | 上游用例表 |
| 运行期断言数 | 11（每例 1 条 EXPECT_TRUE，5+6） | 与 N 同值 |
| 消费者断言数 | 18（+1 编译期 static_assert 单列） | 鸿蒙特有测试行 |

## 交付物

| 文件 | 说明 |
|------|------|
| `include/logfault/logfault.h` | 单头交付件（上游原样，sha256 与源码逐字节一致） |
| `licenses/LICENSE` | 上游 MIT 许可证 |

## 注意事项

- header-only 形态：conan-verify 的 G4/L2/L4/L5 走「跳过」分支（包内无 bin/、无
  lib/*.so）——按 device-facts §二.17 人工补测写 `reports/conan-verify-supplement.md`
  （产物清单↔package_info、消费者真跑、交付件 sha256）。
- **header-only 交付形态·消费者须按 §二人工补测**：消费者面读数见上文验证结果与
  PR 正文。
- 上游 `tests/general_tests.cpp` 是手工开发用例（无 gtest 断言、未被
  `tests/CMakeLists.txt` 引用，上游自身不构建），不参与计数。
- 知识引擎查询（对 gtest C++17 编译失败）命中既有条目 **E292**（testing 类），
  按官方机制不写新草稿；Issue 补交处于冻结状态。
