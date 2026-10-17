# ttmath 0.9.3-src — OHOS 适配笔记

## 结论
- ttmath 是 header-only C++ 模板库（大整数 / 大浮点 / 数学表达式解析器），零运行时依赖，无编译步骤，仅打包头文件。
- 版本号使用官方发布包名 `0.9.3-src`（对应 SourceForge `ttmath-0.9.3-src.tar.gz`，与 Homebrew/Conan 官方配方一致）。
- **无源码补丁**：OHOS aarch64 (clang) 下 ttmath 0.9.3 自动探测到无 x86 宏，选择 `TTMATH_PLATFORM32` + `TTMATH_NOASM` 可移植实现（`ttmathuint_noasm.h`），无需任何平台适配。

## 官方源
- 上游发布包：`https://downloads.sourceforge.net/project/ttmath/ttmath/ttmath-0.9.3/ttmath-0.9.3-src.tar.gz`
- sha256：`4a9a7d1d377fc3907fb75facd4817ba6ac9d60bb4837584256467a54705c6fde`（已本地核验，与 Homebrew formula 一致）
- 源码仓：`https://gitea.ttmath.org/tomasz.sowa/ttmath`（ttmath.org README 标注的官方源）

## 上游测试接入
- 官方 0.9.3 发布包**不含 tests/**；官方测试套件位于 0.9.3 git tag 的 `tests/` 目录（main.cpp、uinttest.cpp、uinttest.h、tests.uint32）。
- 已将 4 个上游测试文件原样 vendored 到 `upstream_tests/`，并在 conanfile.py `build()` 中用工具链 C++ 编译器编译、运行（未改动测试代码）。
- 测试为数据驱动：`tests.uint32` 含 54 条记录（17 ADD / 20 ADDINT / 17 ADDTWOINTS），每条按 `UInt<1..9>` 及 min/max_bits 守卫展开，输出逐条 `[row] Method<size>: ok` 检查行。
- **harness 退出码恒为 0**（不汇总失败），故配方解析输出行数统计真实 executed/passed/failed，并以 `HMBS_UPSTREAM_TEST_RESULT` 机器证据标记报告。
- 实际执行检查数取决于 `TTMATH_BITS_PER_UINT`（官方测试按字长展开）：
  - 本机 GNU/Linux x86_64（64-bit uint，原生 asm）实测：**131 executed / 131 passed / 0 failed**。
  - 本机以 `-DTTMATH_PLATFORM32 -DTTMATH_NOASM` 模拟 OHOS aarch64 配置（32-bit uint + 可移植实现）实测：**158 executed / 158 passed / 0 failed**（57 ADD + 54 ADDINT + 47 ADDTWOINTS；38 条数据记录在当前字长下满足 min/max_bits 守卫）。
  - OHOS aarch64 真机执行数为 runtime 统计（配方 build() 解析 harness 输出行，不硬编码）。

## 证伪验证（防假通过）
- 故意把 `tests.uint32` 中一条 ADD 期望值改成 999 重跑：131 条中 122 ok、9 条 "Incorrect result" —— 证实 harness 与解析逻辑真能抓到失败，退出码 0 ≠ 测试真过。
- 消费者 test.cpp 在打包布局 `include/ttmath/` 下实测 **10 checks / 0 failed**（UInt/Int/Big 运算 + Parser）。

## 配方要点
- `package_type = "header-library"`，`no_copy_source = True`，`package_id()` 清空（无平台二进制）。
- `package()`：复制源码 `ttmath/*` → `include/ttmath/`（保证 `#include <ttmath/ttmath.h>`），COPYRIGHT → licenses。
- `package_info()`：`includedirs=["include"]`，`cmake_target_name = ttmath::ttmath`。
- test_package 用 CMake 消费 `find_package(ttmath)`，test.cpp 含 10 条真实 API 断言。
- 编译器取自 `tools.build:compiler_executables` conf（R33，不裸用 `${CC}`）。

## 版本对齐
- 任务目录 `archives/t/ttmath/0.9.3-src/` = 分支 `feat/ttmath-0.9.3-src` = PR 标题 `feat(ttmath): 0.9.3-src 适配 HarmonyOS PC`。
