# DRAFT-libbig_int-2.6-cmake-install-headers

> 草稿（Path B 知识库扩展）：上游 CMake 仅装库不装头文件的修复与陷阱。待 promote。

## 问题

`libbig_int` 官方 CMakeLists.txt 只有：

```cmake
INSTALL(TARGETS big_int DESTINATION lib)
```

没有任何头文件安装规则。`make install` 产物只有 `lib/libbig_int.a`，Conan 包内
`include/` 为空 —— 消费者 `#include <big_int.h>` 直接编译失败（fatal error:
file not found）。

## 根因

老式单库 CMake 工程只把库目标装入 `lib/`，头文件留在源码树 `include/` 但不参与
install。包化时若不做处理，发布物缺头文件。

## 方案

在 CMakeLists.txt 补一行（见 `archives/l/libbig_int/2.6/patches/0001-CMakeLists.txt.patch`）：

```cmake
INSTALL(DIRECTORY include/ DESTINATION include)
```

**关键陷阱**：`include/` 尾斜杠必须保留。写成 `INSTALL(DIRECTORY include DESTINATION include)`
会把 `include/` 目录整体装进 `include/`，生成 `include/include/*.h` 双层目录，
修复无效（本轮实测先踩中，`make install` 产物为 `usr/local/include/include/big_int.h`，
修正尾斜杠后为 `usr/local/include/big_int.h`）。

## 验证（真实日志）

- `make install DESTDIR=...` 后产物 = `lib/libbig_int.a` + 12 个头文件
  （`basic_funcs.h big_int.h big_int_full.h bitset_funcs.h get_bit_length.h
  low_level_funcs.h memory_manager.h modular_arithmetic.h number_theory.h
  service_funcs.h str_funcs.h str_types.h`）。
- 消费者用例（`test_package/test.c`，仅用公开头 + 静态库）编译链接运行通过，
  10/10 断言，exit 0。

## 适用边界

- 适用：上游 CMake 只 `INSTALL(TARGETS ...)`、头文件在顶层 `include/` 的单库工程。
- 不适用：头文件已装到 `include/<subdir>` 的场景 → 走 E217（改 recipe `package_info()`
  `includedirs`）；框架类工程 install 规则复杂时用回退方案（recipe 内 copy 头文件）。

## 查重差异

- 与 E217（airspyhf）触发域重叠（同为 CMake 头文件安装），但 E217 根因是
  "头文件装进 include/<subdir> 与 includedirs 不匹配"、修复点是 recipe；
  本条根因是"完全不装头"、修复点是上游 patch。方案不可互用，属部分覆盖 + 新增差异。

## 关系

- similar_to: E217
- caused_by / causes / conflicts_with: 无