# physunits-ct 0.1.0 — 适配笔记

## 软件信息

- **名称**: physunits-ct（上游项目 PhysUnits-CT）
- **版本**: 0.1.0（该仓库唯一 tag，2026-09-04 经 GitHub API 交叉验证，commit b9e8f4868ea5）
- **源码**: https://github.com/martinmoene/PhysUnits-CT/archive/refs/tags/v0.1.0.tar.gz
- **SHA256**: c6480f445ad43cc2b76fef1336f692185017ea1a13b795ab944a9ccd2eaf8b7e
- **构建系统**: 无（适配新增 CMake 构建层）
- **许可证**: BSL-1.0
- **与姊妹包关系**: PhysUnits-CT-Cpp11（本仓已适配 1.4.0）是同一作者的 C++11 移植版，两者源码树独立

## 配方设计

- `package_type = "header-library"`，配方导出 `PhysUnits::PhysUnits` INTERFACE target（与 cpp11 包保持同一 target 名，便于下游切换）。
- 上游 v0.1.0 **没有任何构建系统**：只有头文件 `phys/units/*.hpp`、`projects/Test/` 下的 Catch v1 测试和各 IDE 工程文件。补丁 `0001-CMakeLists.txt.patch` 纯新增顶层 CMakeLists.txt，不改任何上游文件：
  - `physunits` INTERFACE target 暴露源码根（上游文档的 `#include "phys/units/quantity.hpp"` 用法）；
  - `PHYS_UNITS_OPT_BUILD_TESTS=ON` 时把上游 7 个测试 TU 编成 6 个 CTest 二进制（Test.cpp 提供 `CATCH_CONFIG_MAIN`；TestCompile.cpp 无注册用例、仅编译期检查，按上游 makefile 目标清单链入每个测试程序）；
  - install 导出 `phys/` 到 `<prefix>/include/phys`。
- 上游 makefile 通过 `CATCH_INCLUDE` 引入外部 catch.hpp；配方 `source()` 以 SHA-256 校验方式下载官方 Catch2 v1.12.2 单头文件到源码根（BSL-1.0，sha256 0c50b1f17c7a9056850c9cb8c6c7c46a4d3d754c2f87941d0d1d16aeb14927e3），仅测试时使用，不是包依赖。
- 无第三方 Conan 依赖；无 OHOS 源码补丁（上游源码零修改）。
- Conan 构建开启上游测试，关闭 examples。

## 设备关键坑（OHOS 特有）

1. **make 无法 exec /bin/sh**：当前设备上 make 自身派生 recipe shell 时被 HMMAC 拒绝（`make: /bin/sh: Permission denied`），且 `ls -la /bin/sh` 同样 Permission denied，但从用户 shell 直接执行 `/bin/sh -c` 与 `/system/bin/sh -c` 正常；make 进程内 exec hnp bash 也正常。这导致 CMake "Unix Makefiles" 生成器的编译器 try-compile 必然失败（`Error 127`）。
   - **解决**：CMake 一律用 Ninja 生成器（ninja 直接 spawn 命令，不经 /bin/sh）。配方通过 `self.conf.define("tools.cmake.cmaketoolchain:generator", "Ninja")` 强制，主包和 test_package 都要设； Conan 2 CMake helper 默认生成器是 "Unix Makefiles"，不强制必踩。
   - 曾尝试 ELF make-shim（execv make 并追加 `SHELL=/data/service/hnp/bin/bash`）：能修 recipe shell，但经 shim 链路后 hnp cmake 加载 `libc++_shared.so` 失败（HMMAC 对从 /storage 发起的库加载链有限制），故放弃 shim 改用 Ninja。
2. **`io::to_string(q)` 编译失败（上游缺陷，不修）**：`quantity_io.hpp` 中 `io::to_string` 模板体内调用 `os << q`，而 `operator<<` 在其之后声明且不属于 ADL 可见范围。C++17/clang15 下消费者报 `error: call to function 'operator<<' that is neither visible...`。这是上游 C++98 头文件的二段查找问题，非 OHOS 特有；消费者测试改用 `to_magnitude()` + `to_unit_symbol()` 组合，`io::eng::to_string()`（独立实现）可用。**未给上游打补丁**，保持上游零修改。

## 测试证据

上游测试：`projects/Test/` 共 7 个 Catch v1 TU。设备实测 6 个 CTest 二进制全部通过：

- TestArithmetic 20 assertions / 2 cases；TestComparison 78 / 1；TestFunction 22 / 4；TestOutput 1 / 2；TestPrefix 29 / 2；TestUnit 271 / 6。
- 合计 **17 个 distinct cases、421 assertions，0 失败 0 跳过**；TestCompile.cpp 与 Test.cpp 不注册用例（后者仅提供 main），故 CTest 总数 6。

统计口径：Catch 输出末行 `All tests passed (N assertions in M test cases)`，N/M 分别为 assertions/cases；executions = CTest 运行的二进制数 × 1。

设备端命令（原生探索与 conan 内部等价）：

```text
cmake -S $SRC -B $BUILD -G Ninja -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 -DCMAKE_BUILD_TYPE=Release -DCMAKE_C_COMPILER=/data/service/hnp/bin/clang -DCMAKE_CXX_COMPILER=/data/service/hnp/bin/clang++ -DPHYS_UNITS_OPT_BUILD_TESTS=ON -DPHYS_UNITS_OPT_BUILD_EXAMPLES=OFF
ninja -C $BUILD
ctest --test-dir $BUILD --output-on-failure
```

Conan `test_package` 为 C++11 consumer（1 个二进制、6 项显式检查）：量纲运算、`to_magnitude`、`to_unit_symbol`、前缀组合、`nth_power`、工程记数，结果 1/1 通过（`PhysUnits-CT consumer checks passed: 6`）。

## 知识库路径判断

本次为路径 A（基础适配）：上游源码零修改，补丁仅新增构建层，CMake/CTest/OHOS settings 均走既有规则（R32、R34、R26、header-only 模式）。

值得关注的可复用观察（供知识库协作者评估是否沉淀）：OHOS 设备 make→/bin/sh exec 被拒、但用户 shell 直接 exec /bin/sh 正常，CMake 改用 Ninja 生成器可绕开；该现象已在本包 manifest.yaml 记录，若其他无构建系统/Makefile 软件再次命中，可升级为正式知识条目。
