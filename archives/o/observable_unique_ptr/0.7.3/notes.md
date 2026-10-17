# observable_unique_ptr 0.7.3 适配笔记

## 编译环境

- 构建系统: cmake（上游根 CMakeLists 为 INTERFACE 目标，header-only 无编译产物）
- 编译日期: 2026-09-28
- 编译器: clang/clang++ 15.0.4（aarch64-unknown-linux-ohos，OHOS SDK native/llvm）
- Conan: 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`（os=OHOS, arch=armv8, cppstd=17）
- 状态: built

## 编译步骤

header-only 库，配方侧四步：

1. `source()`：`get()` 官方 tag 归档
   `https://github.com/cschreib/observable_unique_ptr/archive/refs/tags/v0.7.3.zip`
   （sha256 `7bb69fb686212441c1bb84eac433278e147fa571f45fb084c8343e4fc3198699`，
   与 conan-center-index `recipes/observable_unique_ptr/all/conandata.yml` 的 `0.7.3`
   条目逐字一致，2026-09-28 设备实测下载复核，92223 字节）；
   同时把上游测试框架 snitch v1.3.2（conandata 第二源 `snitch:`）预置到
   `_deps/snitch-src`。
2. `generate()`：`CMakeToolchain` 注入 `OUP_DO_TEST=ON` 与
   `FETCHCONTENT_SOURCE_DIR_SNITCH=<source_folder>/_deps/snitch-src`。
3. `build()`：`apply_conandata_patches()`（`patches: []`，本版本零补丁）→
   `cmake.configure()`（此阶段上游 12 个编译期用例以 try_compile 判定，配方捕获输出
   逐条判读并计数，出现 `FAILED test:` 或计数 ≠12 即失败）→
   `cmake --build --target oup_runtime_tests` → 真实执行 `tests/oup_runtime_tests`，
   解析 snitch 自报计数并落 `HMBS_UPSTREAM_TEST_RESULT=` 机器可读 marker。
4. `package()`：把源 `include/` 树（1 个头 `oup/observable_unique_ptr.hpp`）拷入
   `include/`，`LICENSE` 拷入 `licenses/`；`test_package` 用 CMakeDeps 消费
   `find_package(oup)` + `oup::oup`，编译并执行 25 断言消费者程序。

## 上游测试跑法

上游 `tests/CMakeLists.txt` 用 `FetchContent` 从 `github.com/cschreib/snitch.git`
固定拉取 tag `v1.3.2`——**CI worker 的 git 协议不通 github.com**，直接跑必失败。
处置（libassert-cpp/1.2.1 预置 cpptrace 的同款先例）：snitch 官方 tag zip 写进
conandata 第二源，`source()` 阶段预置到 `_deps/snitch-src`，`FETCHCONTENT_SOURCE_DIR_SNITCH`
指向本地目录，构建期零网络、上游测试文件零改动（不打补丁）。

```sh
# 配方内（conan create 时执行）等价于：
cmake -S <src> -B <build> -DOUP_DO_TEST=ON -DFETCHCONTENT_SOURCE_DIR_SNITCH=<src>/_deps/snitch-src
cmake --build <build> --target oup_runtime_tests
<build>/tests/oup_runtime_tests
# → success: all tests passed (4253 test cases, 30587 assertions, 1.89e-02 seconds)
```

## 上游测试计数（四口径并列，不混用）

| 口径 | 数值 | 取数命令 |
|---|---|---|
| 源码宏数 | 173 | `grep -cE '^\s*TEMPLATE_LIST_TEST_CASE\s*\(' tests/*.cpp` = 170、`grep -cE '^\s*TEST_CASE\s*\(' tests/*.cpp` = 3 |
| 框架注册数（case） | 4253 | snitch 运行自报 `4253 test cases`；= 170 × `owner_types` 25 类型 + 3 |
| 编译期用例 | 12 | `grep -c 'run_compile_test(' tests/CMakeLists.txt`，configure 输出 12 行 `Test … passed.` |
| 断言数（次口径，不作 N） | 30587 | snitch 运行自报 `30587 assertions` |
| 消费者断言（不进上游分母） | 25 | `grep -c '^[[:space:]]*CHECK(' test_package/test_observable_unique_ptr.cpp` |

**申报 N = 4265 = 4253（框架注册数，case 级候选最大值）+ 12（编译期用例）**；
差额逐项归因：源码宏 173 → 注册 4253 是 170 个 `TEMPLATE_LIST_TEST_CASE` 按
`owner_types`（25 个类型）展开的 +4080；注册 4253 → 申报 4265 是 +12 条编译期用例。
断言 30587 属另一统计单位（assertion 而非 case），按四口径不混用原则单列，不作 N。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `tests/CMakeLists.txt` 用 `FetchContent` git clone snitch，CI worker git 协议不通 github.com | 测试框架是测试面依赖，不能进配方 requires，也不能依赖构建期网络 | conandata 第二源 `snitch:` 预置官方 tag zip 到 `_deps/snitch-src` + `FETCHCONTENT_SOURCE_DIR_SNITCH` 指向本地（libassert-cpp 先例），上游测试文件零改动 |
| 2 | 12 个编译期用例失败时 `configure` 退出码仍为 0（`message(WARNING)` 不改 rc） | 上游 `run_compile_test()` 只打 WARNING，不 `FATAL_ERROR` | 配方捕获 configure 输出，逐条判定 `Test … passed.` / `FAILED test:`，计数 ≠12 或有 FAILED 即抛错（反静默） |
| 3 | `test_package` 用 `assert()` 在 Release 下会被 `-DNDEBUG` 编译掉 → 假绿 | CMake Release 默认 `-DNDEBUG` | 改用显式检查 + 计数器 + 非零退出码，25 条断言逐条打印 `[consumer] PASS`，末行 `[consumer] TOTAL=25 FAIL=0` |
| 4 | 平台不可移植性存疑（ISA 专属头 / glibc printf 钩子 / 架构白名单） | W0 生死关判据 | 全 56 文件 grep 命中 0（`altivec|<mmx|3dnow|*mmintrin|register_printf|printf.h|#error Unknown CPU|other architectures are not supported|allowed_architectures`），`#error` 全树 0 命中，无需止损 |

## 上游与仓内关系

- 上游 14 个 tag 全量命中（`git ls-remote --tags`），v0.7.3 → `12c33cc49d9a92b570d8dff2089b630331881f65`；
- 包名与 conan-center-index `recipes/observable_unique_ptr` 一致（config.yml 仅收录 0.7.3）；
- 仓内 `archives/o/observer-ptr-lite` 是另一个项目（martinmoene/observer-ptr-lite），
  与本包不同源、无别名关系，本 PR 不改动它。
