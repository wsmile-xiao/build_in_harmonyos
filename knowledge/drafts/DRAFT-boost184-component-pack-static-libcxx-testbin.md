# DRAFT-boost184-component-pack-static-libcxx-testbin

> 草稿状态：待主编审核提升（`graph promote`）。关联 PR：boost1.84-system 1.84.0 组件包。

## 场景

在 OHOS（鸿蒙 PC）上为 boost 1.84.0 做组件拆分包（boost1.84-system、boost1.84-thread 等），以及任何需要在 conan 流水线里真实运行 libc++ 动态链接测试二进制的配方。

## 问题（两个叠加根因）

1. **b2 不可用**：Boost.Build 的 SHELL 执行机制在 OHOS 不兼容（`common.jam:1164 match-command-output` 失败，E068），`b2 --with-system` / `--with-thread` 裁剪构建无法执行。
2. **测试二进制跑不起来**：OHOS SDK 的 `libc++_shared.so` 在 `llvm/lib/aarch64-linux-ohos/c++` 子目录，conan profile buildenv 的 `LD_LIBRARY_PATH` 只前置 `llvm/lib`（不含 `c++` 子目录）。test_package 的 ctest 与 build() 中编译运行的上游测试二进制动态链接 libc++ 后运行时报：

```
Error loading shared library libc++_shared.so: (needed by ./test_xxx)
Error relocating ./test_xxx: __cxa_begin_catch: symbol not found
```

ctest 判 FAIL → `ConanException: Error 2 while executing cmake.test()` → G2/W3 门禁失败。

## 解决方案（组件包配方模式，4 要点）

1. **独立包名** `boost1.84-<comp>/1.84.0`，conandata 与聚合 `boost/1.84.0` 同源同 sha256，复用已验证 patch（0001-ohos-pthread-cancel-fix）。
2. **build() 手动编译组件 TU 集合**（绕 b2）：
   - system：`libs/system/src/error_code.cpp`（唯一桩 TU）
   - thread：`libs/thread/src/pthread/thread.cpp` + `pthread/once.cpp` + `future.cpp`
   - chrono（thread 的运行依赖，头引用 + 有 3 个 TU）：`chrono.cpp` + `thread_clock.cpp` + `process_cpu_clocks.cpp`
   - flags：`-std=c++17 -stdlib=libc++ -fPIC -DBOOST_ALL_NO_LIB` + 组件专属宏；`llvm-ar rcs` 成 `libboost_<comp>.a`
3. **package()/package_info()**：安装全量 boost/ 头目录（包自包含）；组件 `boost_<comp>`；`cmake_file_name` 用 `<comp>_pkg` 避免与聚合包的 `Boost` config 冲突。
4. **上游测试 + test_package 二进制统一 `-static-libstdc++`**：
   - test_package CMakeLists：
     ```cmake
     if(CMAKE_SYSTEM_NAME STREQUAL "HarmonyOS" OR CMAKE_SYSTEM_NAME STREQUAL "OHOS")
         target_link_options(test_xxx PRIVATE -static-libstdc++)
     endif()
     ```
   - build() 内上游测试编译命令追加 `-static-libstdc++`。
   - 效果：二进制仅依赖 libc.so，干净环境直接可跑。

## 禁止做法

- 硬编码 `LD_LIBRARY_PATH=.../llvm/lib/aarch64-linux-ohos/c++`（worker 环境细节，CI clean 环境失效）。

## 证据

- boost1.84-system：上游 94 测试 93 PASS（1 项 strerror 文本断言为 glibc vs musl 平台差异豁免）；test_package PASS；本 PR。
- boost1.84-url（另一协作者）：PR #8436 CI PASSED，同 `-static-libstdc++` 方案（两例复用）。
- boost/thread 探针：pthread TU + chrono TU 编译链接运行 PASS（thread/mutex/condition_variable/sleep_for 全通）。

## 关联

- E068（b2 OHOS 不兼容根条目）
- E298（test_package 运行环境通用条目；本条目是其 libc++_shared.so/static-libstdc++ 特化）
- DRAFT-boost-headeronly-vendor-meson-boostroot-staging（header-only vendor 模式）
