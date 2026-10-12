# half 7.2.4 适配笔记（ROCm 7.2.4 release train）

## 概述

`half` 是 AMD/ROCm 的 IEEE 754 半精度（binary16）C++ 浮点库（原作者
Christian Rau，现由 ROCm/half 维护）。整个库是**单个自包含头文件**
`include/half.hpp`，没有需要编译的源码。

**版本口径（重要）**：本包 `version = 7.2.4`，跟随 **ROCm 发布列车**（源码标签
`rocm-7.2.4`）；而 `include/half.hpp` 头部注释自报的版本是 **1.12.0**（上游 header
版本），源码包中不存在名为 7.2.4 的头文件版本宏。二者含义不同，勿混淆。

- 官方源（R39）：`https://github.com/ROCm/half/archive/refs/tags/rocm-7.2.4.tar.gz`
- sha256：`8cbe655d3ef19675e953934cf0cb49fdf899459407fbc6848af52282269fc7f9`
- 许可证：MIT（`LICENSE.txt`）

## 编译环境

- 构建系统：header-only（无上游构建；上游附带的 `CMakeLists.txt` 未使用，见下）
- 平台：OpenHarmony / HarmonyOS PC，`os=OHOS`、`arch=armv8`（aarch64）
- 编译器：clang/clang++ 15.0.4（`aarch64-unknown-linux-ohos`），
  `tools.build:compiler_executables` 指向 `/data/service/hnp/bin/clang{,++}`
- Conan：2.29.1（OHOS 适配版）
- profile：`ci/conan/profiles/ohos-aarch64`（os=OHOS arch=armv8 clang 15，
  compiler.libcxx=libc++，compiler.cppstd=17，build_type=Release）
- 状态：built

## 设计决策：为什么不用上游 CMakeLists.txt

上游 `CMakeLists.txt` 做三件事：

```cmake
find_package(ROCM REQUIRED)
include(ROCMSetupVersion)      # rocm_setup_version(VERSION 1.12.0 ...)
include(ROCMCreatePackage)     # rocm_create_package(NAME half ...)
install(FILES include/half.hpp DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/half)
```

`ROCMSetupVersion` / `ROCMCreatePackage` 由**独立的 `rocm-cmake` 包**提供，而
`rocm-cmake` **未发布到 `ohpcd` 制品仓**（`conan install`/`conan download` 均无法
解析）。同时 `half` 是纯 header-only，没有任何需要编译的产物。

按 **PF4 依赖闸 / R36**：配方不得声明一个无法从制品仓解析的
`requires`/`tool_requires`（否则下游构建会 `--build=missing` 或直接失败）。因此本
配方**自包含**：

- `package_type = "header-library"`（Conan 对 header-library 自动清空 package_id）
- `package()` 仅安装上游的完整交付物：
  - `include/half.hpp` → `include/half/half.hpp`
    （与上游 `install(FILES ... DESTINATION ${CMAKE_INSTALL_INCLUDEDIR}/half)`
     完全一致）
  - `LICENSE.txt` → `licenses/LICENSE.txt`
- 不声明任何 `requires`/`tool_requires`

这既满足上游的安装语义，又避免了不可解依赖。

## 编译步骤（conan create）

```bash
export PATH=$HOME/.local/bin:/usr/bin:$PATH
export TMPDIR=$HOME/tmp
REPO='/storage/Users/currentUser/Documents/main/build_in_harmonyos-main (2)/build_in_harmonyos-main'
cd "$REPO/archives/h/half/7.2.4"
conan create . -pr:h="$REPO/ci/conan/profiles/ohos-aarch64" \
               -pr:b="$REPO/ci/conan/profiles/ohos-aarch64"
```

`conan create` 内部：

1. `source()` 从官方 URL 下载并解压（`strip_root=True`）
2. `generate()`：`Environment` 注入 `CXX`/`CXXFLAGS`（编译器取自 Conan toolchain，
   R33：不使用裸 `${CXX}` 之类的 shell 变量）
3. `build()`（层 1 上游测试，见下）
4. `package()` 安装头文件
5. `test_package`（层 2 消费者验证）

## 层 1：上游官方测试（docs/TEST_QUALITY_SPEC.md §3.1）

上游 `test/Makefile` 用 **g++** 手工编译两个测试程序（无 `make check` / `ctest`
目标）：

- `test/src/test03.cpp` — 冒烟程序（half 算术 + `sin`/`ilogb`）
- `test/src/test11.cpp` — 完整的 `half_test` 测试套件，**141 个注册用例**
  （转换/分类/运算符/数学函数/取整等），`main()` 返回**失败用例数**

本配方在 `build()` 中用 OHOS `clang++` 编译并**实际执行**这两个程序（未修改上游
测试源码）：

```text
clang++ -Wall -pedantic -g -O2 -fno-builtin -I <src>/include -o test03 test/src/test03.cpp
./test03                                   # 退出码必须为 0
clang++ -std=c++0x -Wall -pedantic -g -O2 -fno-builtin -I <src>/include -o test11 test/src/test11.cpp
./test11 -fast                             # 运行完整套件并解析汇总
```

- `test03` 退出码 **0**（输出 `0.657715, -1`）。
- `test11` 使用 `-fast` 运行（完整不加 `-fast` 会对 2^32 个 float 全枚举，实测数小时
  级，不适合构建期执行；`-fast` 对 `float_test` 抽样 1e6、对 `binary_test` 按 64 步长
  抽样，其余用例全量枚举，约 1.3s 跑完）。
- `test11` 退出码 **5**：`5 OF 141 FAILED`，失败用例为
  `atan2 / hypot / asinh / acosh / lgamma`。

**为什么这 5 个用例会失败（根因，非配方缺陷）**：`test11.cpp` 用平台
`std::<func>(double)` 作为参考基准，而 `half.hpp` 的数学函数以 **单精度
`float`** 实现（例如 `functions::atan2(float x, float y) { return
expr(std::atan2(x, y)); }`）。单精度实现结果再转 half，与"double 结果直接转
half"在极少数输入上可差 **1 个 half-ULP**（double→float→half 的双重舍入 vs
double→half）。上游 `README.txt` 明确声明"多数函数以单精度实现……存在精度/舍入
考量"。实测复现例（`atan2`，`test11` 迭代的半精度对）：

```text
a=0x0139(1.86563e-05) b=0x00aa(1.01328e-05)
std::atan2(double)=1.0732421194395954
half_float::atan2   = 0x3c4b (1.0732421875)
(half)std::atan2    = 0x3c4a
```

即：与编译器优化级别无关（`-O0` 同为这 5 项；编译期内置替换还会额外引入
`fmin`/`fmax` 假失败，故加 `-fno-builtin` 强制走真实 libm，使结果与 `-O0` 一致）。

**配方处理**：`build()` 运行套件后解析汇总行，**要求失败集合 ⊆ 上述 5 项已知参考
差异**；一旦出现该集合之外的失败（真正的回归）即抛 `ConanException` 令
`conan create` 失败。已知差异仅告警并如实记录。**注意：这是对
TEST_QUALITY_SPEC §3.3「平台限制豁免」的如实申报，而非跳过测试** —— 测试真实
编译执行、产生真实汇总，且非豁免项的失败会硬失败。

> 说明：层 1 要求"断言退出码为 0"。`test03` 满足（退出 0）；`test11` 因上述
> 单精度参考差异退出 5，本配方以"失败集合受控"的方式断言，并在此如实记录偏差与
> 根因，未伪造退出码。

## 层 2：test_package 消费者验证（R34/PF3）

`test_package/` 通过 CMakeDeps 生成的 `half::half` 接口目标链接，
`#include <half/half.hpp>` 并做真实逻辑校验：

- half/float 构造与往返转换（`float → half → float` 精确相等）
- 四则运算、比较运算符
- `std::numeric_limits<half>`（max=65504、digits=11、denorm_min、inf/NaN）
- 边界值：溢出→inf、符号位、0.1f 非精确表示与就近舍入误差
- `half_cast<float>` / `half_cast<int, round_to_nearest>` /
  `half_cast<half, round_to_nearest>`

全部 41 项检查用自实现的 `require()`（失败即 `abort()`）——**刻意不用 `assert()`**，
因为 Conan 的 Release 构建会定义 `NDEBUG`，会使 `assert()` 静默失效变成空壳测试。
`test()` 用 `self.run(..., env="conanrun")` 执行 `test_half` 二进制。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 `CMakeLists.txt` 无法配置 | `find_package(ROCM REQUIRED)` + `rocm_setup_version`/`rocm_create_package` 来自独立 `rocm-cmake` 包，未发布到 ohpcd 制品仓 | 不声明不可解依赖（PF4/R36）；改为自包含 header-only 配方，直接安装 `include/half.hpp` |
| 2 | 包名目录 `half` 但上游构建依赖 `ROCM` 模块集 | 上游把 half 纳入 ROCm 构建体系，而非独立 CMake 包 | 仅采用上游 `install(FILES ... /half)` 的交付语义，安装到 `include/half/half.hpp` |
| 3 | `test11` 退出码非 0（5/141） | `half.hpp` 数学函数以单精度实现，测试以 `std::<func>(double)` 为参考，`atan2/hypot/asinh/acosh/lgamma` 出现 1 个 half-ULP 参考差异（README 已声明） | 运行完整套件并解析汇总；要求失败集合 ⊆ 已知 5 项，否则硬失败；如实记录 |
| 4 | 完整套件（不带 `-fast`）耗时数小时 | `float_test` 枚举全部 2^32 个 float，`binary_test` 枚举全部 half 对 | 构建期以 `-fast` 运行（抽样，约 1.3s），并在报告与文档中说明 |
| 5 | `-O2` 下 `fmin`/`fmax` 额外"失败" | clang 将 `fmin/fmax` 作为内置函数做了与测试语义不符的代码替换 | 加 `-fno-builtin` 强制调用真实 libm，失败集合回到与 `-O0` 一致的 5 项 |
| 6 | 头文件无版本宏 | `half.hpp` 仅在注释中写 "Version 1.12.0"，未暴露 `HALF_VERSION` | 层 2 测试改用 `HALF_HALF_HPP` 包含卫哨证明头文件确实来自本包；版本口径在本文档说明 |

## 源码修改

**无。** 未使用任何补丁（`patches/` 不存在）；上游测试源码
（`test/src/test03.cpp`、`test/src/test11.cpp`）**未做任何修改**。

## 依赖版本

无。`requires`/`tool_requires` 均为空（自包含 header-only 配方）。

## 验证结果（实测）

```text
$ conan create . -pr:h=$REPO/ci/conan/profiles/ohos-aarch64 -pr:b=... 
...
half/7.2.4: Sources correctly downloaded from https://github.com/ROCm/half/archive/refs/tags/rocm-7.2.4.tar.gz
half/7.2.4: [layer-1 1/2] compile + run upstream test/src/test03.cpp
half/7.2.4: RUN: ".../clang++" -Wall -pedantic -g -O2 -fno-builtin -I .../include -o .../test03 .../test/src/test03.cpp
half/7.2.4: RUN: ".../test03"
0.657715, -1                                   # test03 退出码 0
half/7.2.4: [layer-1 2/2] compile upstream test/src/test11.cpp
half/7.2.4: [layer-1 2/2] run the full upstream suite (test11 -fast)
half/7.2.4: upstream test11: 141 cases, exit=5, failed=['acosh', 'asinh', 'atan2', 'hypot', 'lgamma']
half/7.2.4: WARN: upstream test11: only the documented single-precision-vs-double reference differences failed
...
======== Testing the package: Executing test ========
half/7.2.4 (test package): RUN: "./test_half"
test_half: 41 checks passed
```

实测数字汇总：

| 层 | 测试 | 已执行 | 通过 | 失败 | 退出码 |
|----|------|--------|------|------|--------|
| 1 | `test/src/test03.cpp` | 1/1 | 1/1 | 0 | 0 |
| 1 | `test/src/test11.cpp`（`half_test` 套件） | 141 | 136 | 5（已知参考差异） | 5 |
| 2 | `test_package/test_half.cpp`（消费者） | 41 | 41 | 0 | 0 |
| — | `conan create` 整体 | 182 | **177** | 5 | 0 |

- **通过口径（实测）**：executed = 141 + 41 = **182**；passed = 136 + 41 = **177**；
  pass_rate = **177/182 = 97.3%**。层 2 单独为 **41/41 = 100%**。
- 上述 `182` 是**已执行断言数**，`177` 是**通过数**——两者不得混用；
  5 个失败为已声明的平台参考差异，按 TEST_QUALITY_SPEC §3.3 逐条豁免，
  且失败集合受控（集合外任何失败都会让 `conan create` 硬失败）。
- sha256 源码校验：`8cbe655d3ef19675e953934cf0cb49fdf899459407fbc6848af52282269fc7f9`（一致）
- `conan create` 退出码：**0**
- 层 1 用例计数口径：`test11` 自报 `N OF 141 FAILED`（`half_test::tests_` 计数），
  141 为套件注册用例数；`test03` 为打印式冒烟（无断言），退出码 0 即通过。

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | 自包含 header-only 配方（含层 1 上游测试执行） |
| `conandata.yml` | 官方源 URL + sha256 |
| `test_package/` | 层 2 消费者验证（conanfile.py / CMakeLists.txt / test_half.cpp / MANIFEST.yml） |
| `manifest.yaml` | 版本级元数据 |
| `notes.md` | 本文件 |
| `reports/` | conan-verify 报告 + W3 本地 CI 日志 |

## 注意事项

- 本包 `version=7.2.4` **不是** `half.hpp` 的头文件版本（后者为 1.12.0）。
- `include/half/half.hpp` 的安装路径由上游 `install(... DESTINATION .../half)` 决定，
  下游应 `#include <half/half.hpp>`。
- 已知平台参考差异（atan2/hypot/asinh/acosh/lgamma）不影响库本身的 API 与转换正确性
  （层 2 的 41 项真实检查 100% 通过）。
---

**编译结束**: 2026-10-07 10:15
**最终状态**: built
