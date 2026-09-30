# vecgeom 1.2.8 鸿蒙 PC 适配记录（VecGeom）

上游：`https://gitlab.cern.ch/VecGeom/VecGeom`（CERN 官方仓库，tag `v1.2.8`）——
面向高能物理探测器模拟/输运的向量化几何库，C++17 + CMake。

- 源码：`https://gitlab.cern.ch/VecGeom/VecGeom/-/archive/v1.2.8/VecGeom-v1.2.8.tar.gz`
- sha256：`f7a2a0e18560c7d9ff6f974a72313c41ac9f798c65d314c58ecfbc9fa27546f7`（本机 curl 复核一致）
- 分支：`feat/vecgeom-1.2.8`

> 注意：VecGeom 的官方源在 **CERN GitLab**，不是 GitHub；`https://github.com/root-project/vecgeom`
> 不存在（HTTP 404）。

## 1. 依赖（W0）

唯一强制第三方依赖 = **VecCore**（上游 `CMakeLists.txt:208` `set(VecCore_VERSION "0.8.0")`
+ `:222` `find_package(VecCore REQUIRED COMPONENTS ...)`）。

```
conan download veccore/0.8.1 -r=ohpcd --only-recipe   # EXIT=0（可消费）
```

其余 ROOT / Geant4 / CUDA / Embree / GDML(Xerces-C) / VTUNE 均为 **可选且默认关闭**
（`VECGEOM_ROOT/GEANT4` 是 `cmake_dependent_option ... OFF`），OHOS 上一律显式关闭。
`VECGEOM_BUILTIN_VECCORE=OFF`（默认）走外部 VecCore，不内嵌编译。

## 2. 关键决策

- **构建系统 = CMake**（`conan-init` 曾按 autotools 出模板，已改为手写 CMake 配方）。
- **OHOS 平台名**：conan 的 CMakeToolchain 对 `os=OHOS` 默认写 `CMAKE_SYSTEM_NAME=HarmonyOS`，
  而 CMake 只带 `Modules/Platform/OHOS.cmake`，平台变量会全部留空。配方里显式
  `tc.blocks["generic_system"].values["cmake_system_name"] = "OHOS"`（与已合入的 vdt 0.4.4 /
  veccore 0.8.1 同做法）。
- **上游测试真跑**：`BUILD_TESTING=ON` 时 `test/` 被纳入构建；`build()` 内
  `cmake.build()` 之后执行 `ctest --output-on-failure --output-junit upstream-ctest.xml`，
  45/45 通过（脚本汇总行 + JUnit 双证据）。test_package 只做消费者视角的 L1 验证。
- **`transitive_headers=True`（本包最关键的一处配方正确性修复）**：VecGeom 的公开头文件
  （`VecGeom/base/Global.h:20` 等）直接 `#include "VecCore/VecCore"`，对消费者而言 VecCore 是
  **传递头文件依赖**。Conan 2 对 `package_type=library` 的包默认 `transitive_headers=False`
  （只有 header-library 中间包才默认 True），因此必须写
  `self.requires("veccore/0.8.1", transitive_headers=True)`；否则 CMakeDeps 为消费者生成的
  `VecGeom` 目标既不带 VecCore 的 include 目录、也不生成 `find_dependency(VecCore)`，消费者
  编译直接报 `'VecCore/VecCore' file not found`（本机已用最小包对照实验复现并确认）。
- **共享库**：产物为 `lib/libvecgeom.so`（非系统同名库，R26 不要求静态）。安装
  `lib/cmake/VecGeom/VecGeomConfig.cmake`，对外导入目标 `VecGeom::vecgeom`
  （配方侧用 `cmake_file_name=VecGeom` / `cmake_target_name=VecGeom::vecgeom` 对齐）。

## 3. 平台适配问题（首个真实错误 → 根因 → 修复）

### 3.1 `feenableexcept` 在 OHOS sysroot 不存在（编译失败）

- **首个错误**：`VecGeom/base/FpeEnable.h:11:3: error: use of undeclared identifier
  'feenableexcept'; did you mean 'feraiseexcept'?`（在 `test/unit_tests/TestVecGeomPolycone.cpp`
  编译时命中；库本体已 100% 编过）
- **根因**：`feenableexcept()/fedisableexcept()` 是 **GNU libc 扩展**，OHOS sysroot 的
  `<fenv.h>`（musl 系）只提供标准函数（`feclearexcept/feraiseexcept/...`），不提供它们。
  上游只按 `#if defined(__GNUC__) && !defined(__APPLE__)` 守卫，而 clang 会定义 `__GNUC__`，
  于是该块在 OHOS 上被编译。
- **修复**（`patches/0001-VecGeom-base-FpeEnable.h.patch`，+6/-2，零平台宏）：
  1. 把 `#include <fenv.h>` 提到守卫之前（这样 `__GLIBC__` 才可见）；
  2. 构造函数收进 `...#if defined(__GLIBC__)` 能力守卫。
  非 glibc libc 上该 FPE-trapping 测试辅助器退化为 no-op，不影响任何断言语义。
- **重新验证**：补丁 `patch -p1 --dry-run` 干净应用；`conan create` 中该目标编译通过。

### 3.2 aarch64 FMA 收缩导致两个上游用例浮点断言失败

- **现象**：`ctest` 44/45，`TestSphere`（`ApproxEqual(Dist, 100 + 45/sqrt(2))`，TestSphere.cpp:908）
  与 `TestPolyhedra`（`!MyPGon->Contains(pPhiSurface)`，TestPolyhedra.cpp:198）失败。
- **根因**：aarch64 基线含 FMA，clang 自 `-O2` 起默认 `-ffp-contract=on`，把 `a*b+c` 融合成
  一条 FMA，改变浮点结果；上游参考平台 x86-64 无 FMA，不会发生收缩，所以上游测试通过。
- **修复**：配方 `generate()` 里 `tc.extra_cxxflags.append("-ffp-contract=off")`（关闭 FP 收缩，
  与上游 x86 参考数值一致、结果可复现）。
- **重新验证**：`ctest` → `100% tests passed, 0 tests failed out of 45`。

### 3.3 共享宿主上 python 派生编译器静默失败（环境性，不属本库代码问题）

- **现象**：`conan create` 在 CMake 编译器自检处稳定失败：
  `The C compiler ... is not able to compile a simple test program` / `- broken`，
  编译命令无任何 clang 输出、返回码 1；同一命令从交互 shell 直接执行却成功。
- **定位过程**：最小 CMake 工程 + 真实 conan toolchain 手动 configure 均通过；抓 conan 实际构建
  环境的矩阵实验（各 10 次）显示：**由 python（conan 本体）派生 clang 且继承终端 stdin 时失败
  30/30，转由 sh/zsh 派生或把 stdin 重定向为文件/`/dev/null` 时 0/10**。
- **规避**：以 `conan create ... < /dev/null` 运行即稳定通过。该现象与包本身无关，记录为平台/环境
  注意事项（本机为多任务共享宿主，并发负载窗口下更易触发）。

## 3.5 发现与知识（knowledge_gained 索引）

- ✅ [E429-draft-69E4] OHOS sysroot fenv.h（musl）缺 glibc 扩展 `feenableexcept`，需 `__GLIBC__` 能力守卫（见 3.1）
- ✅ [E429-draft-8FC3] aarch64 FMA + clang 默认 `-ffp-contract=on` 改变浮点结果，需关闭 FP 收缩（见 3.2）
- ✅ [E429-draft-5BFE] python（conan）派生 clang 继承 tty stdin 时静默失败，需 `< /dev/null`（见 3.3）
- ✅ [E429-draft-E4C3] OHOS `/tmp` 只读：zsh here-document 用 `$TMPPREFIX` 落盘失败，需重定向到可写目录（W3 门禁前置）
- ✅ [E429-draft-456A] Conan 2 `package_type=library` 的依赖默认非传递头文件，公开头 include 依赖头时需 `transitive_headers=True`（见第 2 节）

## 4. 用例数口径（声明 ≥ 实测 + 取数命令）

源码侧（`test/CMakeLists.txt`）：`TEST_EXECUTABLES_CORE` 经 `add_to_ctest` 注册 29 条
（含 `TestNavigationState`、`testVectorSafety`），shapes 的显式 `add_test` 16 条，合计 45。

实测：

```sh
cd <build-dir> && ctest -N | tail -1     # Total Tests: 45
ctest --output-on-failure                # 100% tests passed, 0 tests failed out of 45
```

无跳过、无排除、无占位。逐用例清单见 `reports/upstream-tests.md`。

## 5. 鸿蒙特有测试用例（≥1）

`test_package/test_ohos.cpp`：仅当 `CMAKE_SYSTEM_NAME == "OHOS"` 时构建并运行。
内容包括 ① 编译期断言 `__OHOS__` 已定义；② 运行时 `uname()`；③ 在鸿蒙上真实构建
`LogicalVolume + UnplacedBox` 世界几何并用 `VPlacedVolume::Inside()` 做点定位取证。
实跑输出：

```
vecgeom/1.2.8 (test package): RUN: ./test_vecgeom
vecgeom consumer test OK: capacity=192000 surface=20800
vecgeom/1.2.8 (test package): RUN: ./test_ohos
test_ohos: uname sysname=AMVS machine=a
test_ohos: OHOS navigation OK (sysname=AMVS)
```

## 6. 验证记录（本机，HarmonyOS PC / aarch64）

- `conan create archives/v/vecgeom/1.2.8 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 < /dev/null` → **EXIT=0**
  - 上游：`100% tests passed, 0 tests failed out of 45`
  - 包：`vecgeom/1.2.8: Package 'dd470a187fa2c17648474ae1121467a85b753d5b' created`
  - test_package：`test_vecgeom` 与 `test_ohos` 均真实运行通过
  - 日志：`.plan/logs_vecgeom/conan-create.log`
- `ohc-run.py conan-verify vecgeom 1.2.8` → **EXIT=0**，G0/G1/G2/G3/G4 + L2/L4/L5 全 PASS
  - 报告：`reports/conan-verify-report.md`

## 7. 边界

- 本包只提供 VecGeom 标量后端库（`VECGEOM_VECTOR` 对非 x86 为 `empty`）；CUDA/ROOT/Geant4/
  GDML/Embree 在 OHOS 上不可用，配方显式关闭。
- 消费者若同时需要 VecCore 头，**无需**自行声明 `requires(veccore)`——已通过
  `transitive_headers=True` 自动传递（但若消费者自有依赖链上另有 VecCore，请保持版本一致）。
- `-ffp-contract=off` 是为数值可复现与上游断言一致而设；若上游后续放宽该断言，可评估移除。
---

**编译结束**: 2026-09-30 09:20
**最终状态**: built
