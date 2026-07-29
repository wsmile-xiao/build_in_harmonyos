# openblas 0.3.34 编译笔记（HarmonyOS PC · Makefile · 含 LAPACK）

## 定位
- 优化 BLAS + 完整 LAPACK。numpy/scipy 等科学计算依赖。产 libopenblas.so.0（含 LAPACK 符号）。

## 关键适配（含 Fortran → 用 flang-ohos）
- LAPACK 是 Fortran，设备/NDK 无 Fortran 编译器 → **tool_requires flang-ohos/20.1.0**（设备原生 LLVM Flang）。
  build() 里 FC=<flang-ohos>/bin/flang，FEXTRALIB 喂 <flang-ohos>/lib/libFortran{Runtime,Decimal}.a。
- **两处源码补丁**（portability）：
  1. exports/Makefile FLANGNEW so 分支：原 $(FC) 当链接器 → flang 塞 host 依赖失败；改 $(CC) 链 + 追加 $(FEXTRALIB)。
  2. blas_server.c：openblas_setaffinity/getaffinity 加 !defined(__OHOS__)（OHOS musl libc.so 不导出 pthread_setaffinity_np）。
- **构建 env**：LD_LIBRARY_PATH = <SDK llvm/lib>:<flang 包 lib>（前者给 lld 正确 libxml2.so.16——HiShell 污染会搞坏 lld；后者给 flang 运行期 libLLVM/libMLIR/libclang-cpp）。CC/AR/RANLIB 用设备 hnp 路径。
- 目标 `shared`（不用默认 all，避免可选 tests 用 flang 当链接器失败）；TARGET=ARMV8。
- package() 里 binary-sign-tool 自签 .so。

## 状态
built（真机原生 conan create 通过：编译+签名+打包；dgemm=[19,43,22,50]、dgesv 解=[1,2] info=0 全对；numpy 2.5.1 链本库验证通过）。

## 2026-07-29 修复：头文件缺失/损坏（package() 改走 make install）

**此前的缺陷**：`package()` 直接从源码树 `copy` 头文件，跳过了 `make install`。而 OpenBLAS 有
三个头是**install 期才产生/加工**的：

| 头文件 | install 期做了什么 | 直接 copy 的后果 |
|---|---|---|
| `openblas_config.h` | 由 `config.h` + `openblas_config_template.h` 拼出 | 源码树里根本没有 → **包里缺失** |
| `f77blas.h` / `lapack.h` | 同样 install 期生成 | **包里缺失** |
| `cblas.h` | `sed 's/common/openblas_config/g'`（`Makefile.install:88`） | 装出的是**内部版**，`#include "common.h"` |

已发布制品实测（修复前）：

```
include/  只有 5 个文件：cblas.h lapacke.h lapacke_config.h lapacke_mangling.h lapacke_utils.h
cblas.h:33  #include "common.h"        ← 包里没有 common.h
```

**任何消费方 `#include <cblas.h>` 都会报 `'common.h' file not found`。**

**为什么长期没被发现**：原 `test_package` 用 `dlopen` + `dlsym`，**从不 include 任何头文件**，
也就永远测不到这条路径。（与 poppler 25.12.0 的 SONAME 缺陷同因——测试不碰的地方，缺陷就能
带着 CI SUCCESS 发布出去。）

**修法**：`package()` 改为 `make <同一套 make 变量> PREFIX=<pkg> install`。
build 与 package 必须用**同一套 make 变量**——`Makefile.system` 依据它们推导库名与安装布局，
两阶段不一致会导致 install 找不到 build 产物；故抽成 `_prepare_env()` 供两处复用
（不用实例属性传递，那样 `export-pkg` 单独跑 `package()` 会 AttributeError）。

顺带收获：`make install` 还会生成 `lib/pkgconfig/openblas.pc` 与
`lib/cmake/openblas/OpenBLASConfig.cmake`，消费方可直接 `find_package(OpenBLAS)` 或 pkg-config。

**同时重写 test_package**：从 dlopen 探针改为**直接链接 + 真实数值计算**，6 条断言——
BLAS 的 `cblas_ddot`/`cblas_dgemm`，LAPACK 的 `dgesv_`/`dpotrf_`/`dgeev_`，逐项校验计算结果。
`#include <cblas.h>` 是其中关键一环：正是它第一次跑就撞出了上述头文件缺陷。

修复后实测：`cblas.h:33 #include "openblas_config.h"`，`include/` 8 个头文件齐全，
`conan create` rc=0（533s），6/6 断言通过。
