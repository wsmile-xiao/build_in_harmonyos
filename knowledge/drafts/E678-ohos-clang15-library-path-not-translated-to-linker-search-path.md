# E678 OHOS 工具链 clang-15 不翻译 LIBRARY_PATH：裸 -l 必须用 link_directories 显式给 -L

> 状态: Draft（待审核 promote）| 日期: 2026-09-29
> 来源: feat/lapackpp-2024.10.26（tester 链接期排障，`-lblaspp` 找不到）
> 机器可读层: 同目录 `E678-ohos-clang15-library-path-not-translated-to-linker-search-path.kv`

## 现象

上游 CMakeLists 有裸名称拼库清单的写法：

```cmake
list(APPEND LAPACK_LIBRARIES "blaspp")   # 生成 -lblaspp，无 -L
```

在 `build()` 里 `export LIBRARY_PATH=<conan 包 lib 目录>` 后链接 tester 仍然失败：

```
ld.lld: error: unable to find library -lblaspp
```

设与不设 LIBRARY_PATH，结果完全相同（empirical 对照实测）。

## 根因

GCC 及部分 clang 驱动会把 `LIBRARY_PATH` 透传为链接器库搜索路径（等价追加
-L）。**本 OHOS 工具链（/opt/lpk-fixed/clang shim → exec clang-15，ld.lld）
实测不翻译**——`LIBRARY_PATH` 对链接搜索零贡献。

容易误判的点：同场景里**头文件**的 `CPATH` 机制正常生效（clang 同语义），
`#include "blas.hh"` 能找到——让人以为"环境变量注入这套好使"，从而漏掉库
路径的坑，或反过来在头文件路径上瞎换方法。

## 解法

裸 -l 名称的解析一律显式给 -L，不依赖环境变量：

1. 配方 `generate()` 把包 lib 目录写入 `tc.variables`（如
   `BLASPP_PKG_LIBDIR=…/lib`）——tc.variables 以 CACHE 变量形式落进
   `conan_toolchain.cmake`；
2. 桥接片段（`CMAKE_PROJECT_<name>_INCLUDE` 注入，见 E671 手法）里
   `link_directories(${BLASPP_PKG_LIBDIR})`——目录作用域，早于
   `add_executable` 生效；
3. 头文件路径用 CPATH（`build()` 里 `os.environ` 注入，只作用于本构建会话）
   或 `include_directories`——两者均实测生效。

## 实测证据（lapackpp/2024.10.26，2026-09-29）

改用 `link_directories` 后 tester 链接成功：产物
`build/Release/test/tester` 为 aarch64 ELF，上游 177 计划项全部 pass
（host_quick PASS=177 FAIL=0，两轮一致）。

## 禁止

- ❌ `export LIBRARY_PATH=…` / `os.environ["LIBRARY_PATH"]=…`：本工具链
  实测不生效，且制造"已提供库路径"的假象，把排障引向错误方向。
- ❌ `LDFLAGS += -L…`：全局污染所有链接单元，与 conan 隔离构建模型相悖，
  CI 静态闸视作环境耦合。

## 对下游的直接复用

一切在本 OHOS 工具链上构建、且上游用裸 -l 名称拼链接行的包（lapackpp、
blaspp 族已实证）。判别法：链接错误带 `unable to find library -l<name>`
且该库实际存在时，先查是否依赖了 LIBRARY_PATH，改走 link_directories。
