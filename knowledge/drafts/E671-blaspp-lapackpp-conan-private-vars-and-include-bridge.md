# E671 BLAS++/LAPACK++ 族在 Conan 下消费 blaspp：私有变量 + 头文件路径双缺口

> 状态: Draft（待审核 promote）| 日期: 2026-09-28
> 来源: feat/lapackpp-2024.10.26（conan create 实测，零补丁通过）
> 机器可读层: 同目录 `E671-blaspp-lapackpp-conan-private-vars-and-include-bridge.kv`

## 现象

`lapackpp/2024.10.26` 在鸿蒙侧做 Conan 适配时，`conan create` 首轮 configure 即红，
两个报错互不相关、却同源：

```
config/config.h:19:6: error: "must define one of FORTRAN_ADD_, FORTRAN_LOWER, FORTRAN_UPPER"
    #error "must define one of FORTRAN_ADD_, FORTRAN_LOWER, FORTRAN_UPPER"

include/lapack/util.hh:15:10: fatal error: 'blas.hh' file not found
#include "blas.hh"
```

前者出现在 `cmake/LAPACKFinder.cmake` / `LAPACKConfig.cmake` 的三个 `try_run` 探针
（`lapack_pstrf` / `lapack_version` / `lapack_xblas`）编译阶段；后者出现在 200+ 个
`src/*.cc` 编译阶段。

## 根因（上游对 blaspp 的"只做一半"消费设计）

上游（icl-utk-edu / SLATE 族）对 blaspp 的依赖有两处"只做一半"，在原生构建
（blaspp 与 lapackpp 同前缀安装，且 blaspp 常以 `add_subdirectory` 并入）下被隐式
满足，换成 Conan 包布局后全部失效：

1. **变量面**。lapackpp 的 `find_package(blaspp)` 唯一目的是取
   `blaspp_defines` / `blaspp_libraries`（上游 `blasppConfig.cmake.in` 末尾注释
   "Export private variables used in LAPACK++"）。但 Conan 的 CMakeDeps 生成的
   `blaspp-config.cmake` **只导出导入目标 `blaspp::blaspp` 与 `blaspp_INCLUDE_DIRS`，
   不导出这两个变量**。探针 include `config/config.h`，而 `config.h` 要求必须定义
   `FORTRAN_ADD_`/`FORTRAN_LOWER`/`FORTRAN_UPPER` 之一（它认 `BLAS_FORTRAN_*`，
   但前提是有人把宏传进来）→ `#error`。

2. **头文件面**。lapackpp 从不 `target_link_libraries(lapackpp PUBLIC blaspp::blaspp)`，
   只 find_package 取变量；而 `include/lapack/util.hh:15` 直接 `#include "blas.hh"`。
   引号包含只搜索 includer 所在目录与 `-I` 路径，原生同前缀安装时该头落在编译器默认
   搜索路径上"能用"；Conan 下每个依赖在各自 `package_folder/include/`，不在任何默认
   路径上 → 全量 TU 报 not found。

## 解法（配方侧，零补丁、上游零改动）

1. 配方**类**属性 `generators = "CMakeDeps"`（`self.generators.append()` 在 recipe
   中不生效，会导致构建树内根本没有 `blaspp-config.cmake`）。
2. `tc.variables["blaspp_defines"]`：**从已安装的 blaspp 包的
   `include/blas/defines.h` 反解**（跳过 include guard `BLAS_DEFINES_H`）。
   该文件是 BLAS++ 构建期 `configure_file` 生成的权威配置记录，携带命名修饰
   （`BLAS_FORTRAN_ADD_`/`LOWER`/`UPPER`）与能力位（`BLAS_HAVE_CBLAS`）。
   本次实测反解得到 `-DBLAS_FORTRAN_ADD_;-DBLAS_HAVE_CBLAS`。
   **刻意不硬编码** `-DBLAS_FORTRAN_ADD_`——后端是 LP64/ILP64 × ADD_/LOWER/UPPER
   四种组合，硬编码等于把当前后端焊死；且 `config.h` 的 `#error` 只校验"定义了一个"，
   **不校验"定义对了"**，链错符号要到链接期甚至运行期才暴露。3. `tc.variables["blaspp_libraries"]`：与 `BLAS_LIBRARIES` 同源的库清单（探针链接用）。
4. include 路径见 E673（`CMAKE_PROJECT_<name>_INCLUDE` 注入桥接片段）。

## 实测证据（lapackpp/2024.10.26，2026-09-28 WSL 本地 conan create）

```
Found BLAS++: /root/.conan2/p/b/lapacdc58721e401ea/b/build/Release/generators
   Found LAPACK library: .../liblapack.a;.../libFortranRuntime.a;.../libFortranDecimal.a;m
-- Checking LAPACK version
   LAPACK version 3.12.00 (31200)
   XBLAS not found.
   LAPACKE library not found. Tester cannot be built.
→ W3_RC=0, 205s, 0 error, test_package 18/18 断言通过
```

注：`LAPACK version 3.12.00` 是 `try_run` 探针**真实执行**得来的输出，不是配方写死的
——`LAPACK_VERSION` 缺失会让 20+ 个 `src/*.cc` 的 `#if LAPACK_VERSION >= 30700`
静默走错分支，属必须保证的真实值。

## 禁止

- ❌ 硬编码 `tc.variables["blaspp_defines"] = "-DBLAS_FORTRAN_ADD_"`。
- ❌ 复用 blaspp 包内上游安装生成的 `blasppConfig.cmake`——实测其内嵌**构建机绝对路径**
  （`/storage/Users/currentUser/.cache/conan2/...`），换机即失效。
- ❌ `self.generators.append("CMakeDeps")`（recipe 中不生效）。

## 对下游的直接复用

SLATE 本体及任何以 Conan 消费 blaspp 的包，同一套配方侧桥接原样可用；
`blaspp-libraries-passthrough`（E667）提供的库清单与静态链接拓扑序继续适用。
