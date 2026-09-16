# libint2 2.7.2 测试报告

> **项目**: libint2
> **测试日期**: 2026-09-13
> **测试环境**: HarmonyOS PC（HongMeng Kernel 1.12.0，aarch64，20 core），clang/clang++ 15.0.4
> **测试类型**: 上游官方测试套件（CTest）+ Conan 消费者测试（4 个独立入口）

---

## 一、测试摘要

| 指标 | 数值 | 百分比 |
|:----:|:----:|:------:|
| 上游 CTest 用例总数 | 12 | 100% |
| 通过 (PASS) | 12 | 100% |
| 失败 (FAIL) | 0 | 0% |
| 跳过 (SKIP) | 0 | 0% |
| 新增消费者入口 | 4 | 100% |
| 新增断言 | 38 | 100% |

**核心功能通过率**: ✅ **100%**

补充（上游 Catch2 单元测试内部断言）：**2,104,689 断言 / 17 test case，全部通过**。

---

## 二、测试结论

### 2.1 总体评价

✅ **通过**：上游 CTest 12/12 全过（含 2.1M 断言的单元测试与 HF 能量校验）；Conan 消费者测试
4 个独立入口全部编译、链接、运行通过（`failures = 0`）。

### 2.2 主要问题

| 问题类别 | 影响范围 | 严重程度 |
|----------|----------|----------|
| 测试二进制运行期缺 `libc++_shared.so`（OHOS clang 默认动态链 C++ 运行时） | 全部 8 个 run 用例（首次运行 33% 通过率） | 🟡 已修复（`-static-libstdc++`，见 §四.1） |
| 消费者侧缺 Eigen include（header-only 依赖未传递） | test_package 编译失败 | 🟡 已修复（`transitive_headers=True`，见 §四.2） |
| 安装出的 `libint2.pc` 前缀/版本为空（上游模板渲染缺陷） | pkg-config 消费契约（第二消费契约）完全不可用且静默失败 | 🟡 已修复（`package()` 用 `${pcfiledir}` 重写，见 §四.3） |

### 2.3 可用功能清单

```
✅ 1 电子积分引擎（overlap / kinetic / nuclear / emultipole / sphemultipole）
✅ 2 电子库仑积分（SS/SP/PP/…，最大角动量 l=6，generic code + FMA）
✅ 3 中心/2 中心积分（pure-sh 配置）
✅ C API（内核分发表 / 内存查询 / init-cleanup 生命周期）
✅ C++11 API（libint2::BasisSet / libint2::Engine）
✅ 基组数据库按名加载（STO-3G / 6-31G* / cc-pVDZ / aug-cc-pVDZ 等）
✅ Hartree-Fock 积分流水线（能量与参考值 -74.942080057696 吻合）
✅ 消费契约：CMake config（Libint2::int2）+ pkg-config（重写后的 .pc）
```

### 2.4 已知限制

1. Fortran 绑定未启用（`ENABLE_FORTRAN=OFF`，环境无 Fortran 2003 编译器）。
2. 本归档使用上游 Release 的 **exported library** tarball（kernel 源码预生成）；
   如需自定义积分类型/角动量，需要 libint 编译器路线（GMP/Boost/CMake + 数小时代码生成），不在本次范围。
3. `LIBINT2_ENABLE_MPFR`（高精度测试）默认关闭（需 MPFR/GMP C++ 接口）。
4. 消费者入口 2（C ABI）验证的是内核分发表/内存契约/生命周期；数值正确性由上游
   `tests/unit/c-api.c`、`test-c-api.cc` 与入口 1/3 覆盖，未重复断言。

---

## 三、测试详情

### 测试命令

```bash
# 上游测试（conanfile.py build() 内真实执行，R51）
ctest --output-on-failure -R libint2/        # 100% tests passed, 0 tests failed out of 12

# 消费者入口（conan create 的 test 阶段逐个执行）
./test_package      # C++ API
./test_c_api        # C ABI
./test_basis        # 基组数据库
# 入口 4：pkg-config 消费契约
clang -std=c11 $(pkg-config --cflags libint2) test_pkgconfig.c -o test_pkgconfig $(pkg-config --libs libint2)
```

### 3.1 通过的测试（上游 CTest，12/12）

| # | 测试项 | 功能 | 结果 | 耗时 |
|---|--------|------|------|------|
| 1 | `libint2/eritest/build` | 构建 ERI 对比测试（fixture） | ✅ PASS | 64.45s |
| 2 | `libint2/eritest/run0` | ERI 内核对比（`eritest 0 2`，ss 系列） | ✅ PASS | 4.61s |
| 3 | `libint2/eritest/run1` | ERI 内核对比（`eritest 1 1`，sp） | ✅ PASS | 0.13s |
| 4 | `libint2/eritest/run2` | ERI 内核对比（`eritest 2 1`，pp） | ✅ PASS | 0.11s |
| 5 | `libint2/eritest/run3` | ERI 内核对比（`eritest 3 1`，sd/ds） | ✅ PASS | 0.12s |
| 6 | `libint2/eritest/run4` | ERI 内核对比（`eritest 4 1`，更高角动量） | ✅ PASS | 0.12s |
| 7 | `libint2/unit/build` | 构建 Catch2 单元测试（fixture） | ✅ PASS | 277.29s |
| 8 | `libint2/unit/run` | 单元测试 17 case / 2,104,689 断言 | ✅ PASS | 1.15s |
| 9 | `libint2/hf/build` | 构建 Hartree-Fock 测试（fixture） | ✅ PASS | 78.42s |
| 10 | `libint2/hf/run` | H2O/STO-3G HF 流水线 + 能量校验（参考 -74.942080057696，tol 1e-11） | ✅ PASS | 0.26s |
| 11 | `libint2/hf++/build` | 构建 HF++（C++ API，多线程）（fixture） | ✅ PASS | 90.69s |
| 12 | `libint2/hf++/run` | H2O（旋转坐标）HF++ 流水线 + 校验脚本 | ✅ PASS | 0.70s |

**汇总**：`100% tests passed, 0 tests failed out of 12`

上游单元测试 17 个 test case 明细（`unit_tests-libint2 --list-tests`）：
`electrostatic potential`、`Slater/Yukawa integrals`、`bra-ket permutation`、
`eri geometric derivatives`、`Basis`、`C API`、`Shell ctor`、`Engine ctor`、
`Engine::set`、`cartesian uniform normalization`、`Slater/Yukawa core integral values`、
`2-e 4-c integrals permute correctly`、`2-e 3-c integrals permute correctly`、
`2-e 2-c integrals permute correctly`、`2-body integrals precision`、
`solid harmonics`、`XYZ reader`。

### 3.2 失败的测试

无。

### 3.3 跳过的测试

无（12/12 全部真实执行）。

### 3.4 消费者入口（conan create 自动执行，4/4）

| # | 入口 | 覆盖面 | 断言 | 结果 |
|---|------|--------|------|------|
| 1 | `test_package`（C++） | C++ API：`BasisSet("sto-3g")` 加载、重叠矩阵对角元==1、对称性（实测最大偏差 5.55e-17）、库仑积分 `(00\|00)=4.78507`、置换对称、同中心 s×p 宇称零元、Schwarz 不等式 | 9 | ✅ `failures = 0` |
| 2 | `test_c_api`（C） | C ABI：`libint2_build_{overlap,kinetic,elecpot,1emultipole,2emultipole,eri,3eri,2eri}` 分发表注册、`need_memory_eri` 单位（`LIBINT2_REALTYPE` 元素个数）与单调性、调用方 buffer 的 init/cleanup 契约 | 17 | ✅ `failures = 0` |
| 3 | `test_basis`（C++） | 基组数据：`sto-3g`(7)、`6-31g*`(19)、`cc-pvdz`(24)、`aug-cc-pvdz`(41) 按名加载 + max_l；负向：未知名默认空基组、strict 抛异常且信息含真实数据目录 | 11 | ✅ `failures = 0` |
| 4 | `test_pkgconfig`（C） | pkg-config 消费契约：`pkg-config --cflags/--libs libint2` 的返回值真实编译并运行（对 `.pc` 重写的回归守卫） | 1 | ✅ `[PASS] pkg-config consumer: C API 可用 (need_memory_eri(1) = 14133)` |

> 入口 4 的取证价值：修复前 `pkg-config --cflags` 返回 `-I -I/libint2`（空前缀）→ 编译必然失败；
> 修复后返回 `<pkg>/include` 系列真实路径 → 编译运行通过。

---

## 四、关键问题分析

### 问题 1: 上游测试二进制运行期 `Error loading shared library libc++_shared.so`

**现象**：

```
2/12 Test  #2: libint2/eritest/run0 .............***Failed    0.28 sec
Error loading shared library libc++_shared.so: (needed by /.../eritest-libint2)
Error relocating /.../eritest-libint2: __cxa_throw: symbol not found
Error relocating /.../eritest-libint2: _ZTVSt16invalid_argument: symbol not found
33% tests passed, 8 tests failed out of 12
```

**根因分析**：`readelf -d` 显示产物 `NEEDED libc++_shared.so` 且无 RUNPATH；该库只存在于
SDK sysroot（`.../llvm/lib/aarch64-linux-ohos/`），不在设备默认库搜索路径。

**解决方案**：`conanfile.py generate()` 中
`tc.variables["CMAKE_EXE_LINKER_FLAGS"] = "-static-libstdc++"`
（test_package 侧 `target_link_options(... -static-libstdc++)`）。
只影响可执行文件链接，静态库产物不受影响。修复后 12/12 通过。

### 问题 2: test_package 编译失败 `fatal error: 'Eigen/Core' file not found`

**根因分析**：Eigen 是 header-only 依赖（Conan 图中 `binary=Skip`），默认
`transitive_headers=False` 时被视为纯实现依赖，消费者侧 CMakeDeps 不生成 `Eigen3` config；
而 libint2 的**公开头文件**（`libint2.hpp` → `engine.h` → `Eigen/Core`）需要它。

**解决方案**：`self.requires("eigen/3.4.0", transitive_headers=True)`。
对照实验：无该 trait 时消费者侧生成的 `libint2-release-armv8-data.cmake` 中
`FIND_DEPENDENCY_NAMES` 为空，且不生成 `Eigen3Config.cmake`；加上后两者都出现。

### 问题 3: 安装出的 `libint2.pc` 前缀/版本为空，`pkg-config` 静默给出垃圾标志

**现象**（修复前，实测）：

```console
$ PKG_CONFIG_PATH=<pkg>/lib/pkgconfig pkg-config --cflags --libs libint2
-I -I/libint2 -L -lint2          # exit code 仍为 0
```

**根因分析**：`libint2.pc.in` 用 autotools 变量（`@prefix@`/`@libdir@`/`@PACKAGE_VERSION@`…），
而 exported library 走 CMake，只做 `configure_file(... @ONLY)`，未定义占位符被替换为空串。

**解决方案**：`package()` 中用可重定位的 `${pcfiledir}/../..` 重写 `.pc`，并由消费者入口 4 回归守卫。

---

## 五、测试环境

```
平台         : HarmonyOS PC / aarch64（HongMeng Kernel 1.12.0），20 core，31 GB RAM
编译器       : clang/clang++ 15.0.4（OHOS SDK llvm）
Conan        : 2.29.1（OHOS 适配版）
Profile      : ci/conan/profiles/ohos-aarch64（os=OHOS 6.0, arch=armv8, clang 15, libc++, cppstd=17）
依赖         : eigen/3.4.0（header-only）；Boost.Preprocessor 使用包内 bundled 副本
构建系统     : CMake 4.1.2（Unix Makefiles），-j20
配方         : archives/l/libint2/2.7.2/conanfile.py
```

### 日志路径

| 日志 | 路径 |
|------|------|
| W3 本地 CI 完整日志（含 ctest 12 项 + 4 个消费者入口输出） | `archives/l/libint2/2.7.2/reports/w3-local-ci.log` |
| conan-verify G2 日志 | `archives/l/libint2/2.7.2/reports/conan-create.log` |
| conan-verify 门禁报告 | `archives/l/libint2/2.7.2/reports/conan-verify-report.md` |
| 手工构建 ctest（修复前，8 项失败） | `/data/storage/el2/base/temp/logs/libint2-manual-ctest.log` |
| 手工构建 ctest（修复后，12/12） | `/data/storage/el2/base/temp/logs/libint2-manual-ctest2.log` |
| 上游单元测试直跑输出（2,104,689 断言） | `/data/storage/el2/base/temp/logs/libint2-upstream-unit-tests.log` |
| 上游 hf 直跑输出（能量 -74.942080057696） | `/data/storage/el2/base/temp/logs/libint2-upstream-hf.log` |

---

## 六、CI 门禁结果（本地 W3 模拟）

```
JC_RESULT=pass        # junk check（含 JC6 单软件原子性：涉及软件数 1，合规）
KC_RESULT=pass        # knowledge check（0 errors）
L0_RESULT=pass: all checks passed
L1_RESULT=pass: upstream tests + test_package executed
```

---

*报告生成时间: 2026-09-13*
