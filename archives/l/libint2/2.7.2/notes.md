# libint2 2.7.2 适配笔记

## 编译环境
- 构建系统: cmake（上游 release 资产 `libint-2.7.2.tgz` 是 exported library，自带 CMakeLists.txt）
- 编译日期: 2026-09-13
- 编译器: clang/clang++ 15.0.4（OHOS SDK，`/data/service/hnp/bin/clang++`）
- 目标平台: OpenHarmony / HarmonyOS PC，aarch64（原生构建，非交叉）
- Conan: 2.29.1（OHOS 适配版），profile `ci/conan/profiles/ohos-aarch64`
- 状态: built

## 编译步骤

1. **源码**：上游 GitHub Release 资产 `libint-2.7.2.tgz`（37.4 MB，sha256
   `a7306f1998a4c0a0babc13d480c62de2631674918e3562c78fb602c77efe0b94`）。
   该资产是 **exported library**：libint *编译器* 侧的代码生成本已在上游完成
   （`src/` 6520 个 `.cc`），并自带上游 CTest 测试（`tests/`）。

   > 注意：GitHub 仓库 master/tag 的源码树走 autotools（`configure.ac`/`autogen.sh`）
   > 且需要先构建编译器（依赖 CMake+Boost+GMP），耗时数小时；适配口径应使用官方
   > Release 的 exported tarball。

2. **依赖**：`eigen/3.4.0`（C++ API 必需，公开头文件 `#include <Eigen/Core>`，
   声明 `transitive_headers=True`）。Boost 为可选依赖——系统无 Boost 时上游自动
   解包包内 `external/boost.tar.gz`（Boost.Preprocessor）并把
   `include/libint2/boost` 安装进包，因此不引入 boost 依赖；GMP/MPFR 仅 libint
   编译器需要，本路径不涉及。

3. **构建**（`conan create`）：
   ```bash
   conan create archives/l/libint2/2.7.2 \
     -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
     --build="libint2/*"
   ```
   `generate()` 中固化上游默认值：`REQUIRE_CXX_API=ON`、`ENABLE_FORTRAN=OFF`、
   `BUILD_SHARED_LIBS=OFF`（默认静态库），并追加
   `CMAKE_EXE_LINKER_FLAGS=-static-libstdc++`（见问题 1）。

4. **打包修正**：`package()` 里 `cmake.install()` 之后重写安装出来的
   `lib/pkgconfig/libint2.pc`（上游模板渲染缺陷，见问题 7）。

5. **上游测试**：`build()` 内执行 `ctest --output-on-failure -R "libint2/"`，
   12 个 CTest 用例（4 个 build fixture + 8 个 run）全过。

6. **消费者入口**：`test_package` 提供 4 个独立入口（C++ API / C ABI / 基组数据 /
   pkg-config 契约），`conan create` 的 test 阶段全部真实执行。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游测试二进制运行期失败：`Error loading shared library libc++_shared.so` + `Error relocating … _ZTVSt16invalid_argument: symbol not found`（ctest 12 项中 8 项 run 用例挂） | OHOS clang 15 用 `-stdlib=libc++` 默认把可执行文件动态链到 `libc++_shared.so`，该库只在 SDK sysroot（`.../llvm/lib/aarch64-linux-ohos/`），不在设备默认库搜索路径，产物也无 RUNPATH | `generate()` 中设 `CMAKE_EXE_LINKER_FLAGS=-static-libstdc++`（只影响 exe 链接，静态库产物不受影响）；test_package 侧 `target_link_options(... -static-libstdc++)`。修复后 ctest 12/12 通过。回退方案（已验证）：把 SDK `aarch64-linux-ohos` 目录前置到 `LD_LIBRARY_PATH` |
| 2 | 首次 `conan create` 的 test_package 编译失败：`fatal error: 'Eigen/Core' file not found` | libint2 公开头文件（`engine.h`→`Eigen/Core`）需要 Eigen，但 eigen 是 header-only 依赖，`binary=Skip`；默认（`transitive_headers=False`）时 Conan 视为实现依赖，消费者侧 CMakeDeps 不生成 `Eigen3` config，也不加 include 路径 | 配方里改为 `self.requires("eigen/3.4.0", transitive_headers=True)`。实测可让消费者侧生成 `Eigen3Config.cmake` 并传递 Eigen include（对照实验：无该 trait 时生成的 `libint2-release-*-data.cmake` 中 `FIND_DEPENDENCY_NAMES` 为空） |
| 3 | 上游静态库文件名与包名不一致的风险 | 上游 `set_target_properties(libint2 PROPERTIES ARCHIVE_OUTPUT_NAME int2)` → 产物为 `libint2.a`（库名 `int2`） | `package_info()` 写 `cpp_info.libs = ["int2"]`（不按包名猜） |
| 4 | `BasisSet("sto-3g", atoms)` 按名加载基组会失败 | 上游 `basis.h` 的数据目录来自编译期宏 `DATADIR`/`SRCDATADIR` 或环境变量 `LIBINT_DATA_PATH`，Conan 包装后没有对应 define，退回构建期写死的绝对路径 | `package_info()` 追加 `DATADIR="<pkg>/share/libint/2.7.2"`；test_package 增加基组数据入口（正向 4 个基组 + 负向 2 个断言，负向断言要求异常信息里出现真实数据目录） |
| 5 | CMake 报 `System is unknown to cmake, create: Platform/HarmonyOS` | CMake 4.1.2 未内置 HarmonyOS host 平台文件 | 仅提示，不影响配置/构建；无需处理 |
| 6 | `init-build` 误判构建系统为 autotools | `init-build` 按下载 URL 扩展名猜测（`libint-2.7.2.tgz` 无构建系统信息） | 在版本级 `manifest.yaml` 中修正 `build_system: cmake`；`conan-init` 据此选用 cmake 模板 |
| 7 | 安装出来的 `libint2.pc` 不可用：`prefix=`、`Version:` 为空，`pkg-config --cflags --libs libint2` 返回 `-I -I/libint2 -L -lint2`（且 exit 0，静默失败） | `libint2.pc.in` 沿用 autotools 变量（`@prefix@`/`@libdir@`/`@PACKAGE_VERSION@`…），而 exported library 走 CMake，只做 `configure_file(... @ONLY)`：未定义占位符被替换成空串 | `package()` 中用可重定位的 `${pcfiledir}/../..` 重写 `.pc`（补齐 Name/Version/Libs/Cflags），并新增 pkg-config 消费入口做回归守卫（`test_package/test_pkgconfig.c`，用 `pkg-config` 的返回值真实编译+运行） |

## 源码修改

无补丁（`patches/` 为空）。所有适配都在配方层完成：
`CMAKE_EXE_LINKER_FLAGS=-static-libstdc++`、`CMakeDeps`、
`package_info()` 的 `libs` / `DATADIR` / `transitive_headers`、`package()` 的
`.pc` 重写，未改动上游源码。

## 依赖版本

- eigen/3.4.0（header-only，OHOS 预编译包已发布；`transitive_headers=True`）
- Boost：未使用 Conan 包，走包内 bundled Boost.Preprocessor
- Python 3.12.9（`find_package(PythonInterp)`，仅用于上游 hf 测试的校验脚本，纯标准库）

## 消费者入口矩阵（test_package）

| # | 入口 | 覆盖面 | 断言数 | 结果 |
|---|------|--------|--------|------|
| 1 | `test_package`（C++） | C++ API：BasisSet + Engine，重叠矩阵归一化/对称、库仑积分置换对称/宇称零元/Schwarz | 9 | 全过 |
| 2 | `test_c_api`（C） | C ABI：`libint2_build_*` 内核分发表、`libint2_need_memory_eri`（返回值单位是 `LIBINT2_REALTYPE` 元素）、调用方 buffer 的 init/cleanup 契约 | 17 | 全过 |
| 3 | `test_basis`（C++） | 基组数据库：sto-3g / 6-31g* / cc-pvdz / aug-cc-pvdz 按名加载；未知名默认空基组、strict 模式抛异常且信息含数据目录 | 11 | 全过 |
| 4 | `test_pkgconfig`（C） | pkg-config 消费契约：用安装出来的 `libint2.pc` 的 `--cflags/--libs` 真实编译并运行 | 1 | 全过 |

入口 4 是对问题 7 的回归守卫：若 `.pc` 再次退化为空前缀，该入口会编译失败。

## 知识库扩展（复用 / 新增 / 去重）

**复用既有正式条目**：E480（header-only 依赖用 `transitive_headers=True` 消费）、
E216（CMakeDeps 不传播依赖 include，消费者编译失败）、E092（CMake 不识别
HarmonyOS host 平台）、E247（上游 .pc 元数据不完整的同类）。

**本次新增草稿（KV+MD 配套，draft 形式随 PR 提交，不改进正式 index）**：

| 草稿 | 问题面 | 预审建议 |
|------|--------|----------|
| `DRAFT-libint2-2.7.2-upstream-pc-template-unrendered-by-cmake` | 上游 .pc 模板经 CMake `configure_file(@ONLY)` 渲染后前缀/版本为空（问题 7） | create（新知，最高相似 0.22） |
| `DRAFT-libint2-2.7.2-cpp-info-libs-must-use-upstream-output-name` | `OUTPUT_NAME` 覆盖包名时 `cpp_info.libs` 必须按产物取值（问题 3） | review-similar（灰区 0.30 → E511） |
| `DRAFT-libint2-2.7.2-compile-time-datadir-macro-for-runtime-data` | 运行期数据目录靠编译期宏定位，须在 `package_info()` 补 define（问题 4） | create（新知） |

**去重记录**：适配过程中先写过一条
`DRAFT-libint2-2.7.2-static-libcxx-for-test-binaries`（问题 1 的 libc++ 运行时教训），
经检索发现仓库已有同因同方案的草稿
`DRAFT-boost184-component-pack-static-libcxx-testbin`
（"用 `-static-libstdc++` 烘入 libc++ 解决 OHOS buildenv 加载不了 libc++_shared.so"），
故**删除该重复草稿**，本节与 README 以引用方式使用既有草稿，不重复入库。

## 验证结果

见 `reports/test-report.md`（上游 ctest 逐项统计 + 消费者入口逐项结果）、
`reports/w3-local-ci.log`（W3 本地 CI 完整日志）与 `reports/conan-create.log`
（conan-verify G2 完整日志）。

## 注意事项

- **构建规模**：6520 个 kernel 源文件，20 核并行全量编译约 18-20 分钟；本地 W3 完整
  CI 模拟（强制重建 + 上游 ctest + test_package + L4/L5 门禁）实测约 29.5 分钟
  （20:42:51 → 21:12:14，≈1763s），在 CI 默认 3600s 预算内（余量约 52%）。
- **不要用 GitHub 仓库源码树 + autotools 路径**：会先构建 libint 编译器（GMP/Boost/CMake
  依赖 + 代码生成），耗时数小时，且与本归档的 Release 资产口径不一致。
- 上游 ctest 的 test 可执行文件是 `EXCLUDE_FROM_ALL`，由 ctest 的 build fixture 先构建再运行；
  因此 `cmake.build()` 只出静态库是正常的。
- `libint2_need_memory_eri()` 的返回值单位是 `LIBINT2_REALTYPE` **元素个数**（本配置为 double），
  调用方须按 `need * sizeof(LIBINT2_REALTYPE)` 分配；且 `libint2_cleanup_eri()` 会
  `free(inteval->stack)`——buffer 移交给库之后调用方不得再次释放。
---

**编译结束**: 2026-09-13 22:17
**最终状态**: built
