# DRAFT — autotools configure.ac 把 C++ 专用 -std= 注入 CPPFLAGS 导致 C 源编译失败

> 配对 .kv：`DRAFT-irstlm-6.00.05-cxx0-in-cppflags-breaks-c-build.kv`
> 来源：irstlm 6.00.05（2026-09-21 适配，任务 irstlm-6.00.05-r01-pc1-56）

## 问题

irstlm 6.00.05 首次 `make` 时 C 源（`src/cmd.c`）编译立即失败：

```
libtool: compile: clang ... -DHAVE_CXX0 -std=c++0x -fPIC -O2 ... cmd.c -o cmd.o
error: invalid argument '-std=c++0x' not allowed with 'C'
make[2]: *** [Makefile:747: cmd.lo] Error 1
```

C++ 源（dict.cpp 等）正常，只有 C 源中招。

## 根因

上游 `configure.ac` 用一行同时注入宏与 C++ 标准：

```m4
CPPFLAGS="$CPPFLAGS -DHAVE_CXX0 -std=c++0x";
```

autotools 中 **CPPFLAGS 同时作用于 C 与 C++ 编译**（两语言的 Makefile 规则都会带上
CPPFLAGS/AM_CPPFLAGS）。C++ 专用标志 `-std=c++0x` 被 C 编译器拒绝。
该库是 C/C++ 混编（cmd.c、thpool.c 为 C 源，其余为 C++ 源），所以 C 源首编即败。

## 修复（irstlm 6.00.05 验证通过）

补丁 `patches/0002-configure.ac.patch`：

```diff
-    CPPFLAGS="$CPPFLAGS -DHAVE_CXX0 -std=c++0x";
+    CPPFLAGS="$CPPFLAGS -DHAVE_CXX0";
+    CXXFLAGS="$CXXFLAGS -std=c++0x";
```

- `-DHAVE_CXX0`（预处理宏）留在 CPPFLAGS：C 与 C++ 源都需要的头文件开关；
- `-std=c++0x`（C++ 专用方言）移到 CXXFLAGS：只有 C++ 编译规则携带。

## 验证

- 补丁应用后 `make -j1` 全绿（C 源 cmd.lo/thpool.lo 正常，C++ 源保留 -std=c++0x）；
- `conan create`（ohos-aarch64）全绿，test_package 1/1 Passed；
- finish W3 本地 CI 100%。

## 适用条件

- C/C++ 混编 autotools 项目；
- configure.ac（或 Makefile.am 的 AM_CPPFLAGS/CFLAGS）把 `-std=c++*` 或其它
  C++ 专用选项注入 CPPFLAGS/CFLAGS（两语言共用变量）。

## 边界 / 限制

- **反例/勿做**：不能直接丢弃 -std=（C++ 源可能依赖该方言特性）；不能改注入
  CFLAGS（CFLAGS 同样作用于 C 编译）；
- CMake 语境有同族现象但根因不同：上游 CMakeLists 用普通变量 `set(CMAKE_CXX_STANDARD)`
  遮蔽 toolchain 注入的 cache 标准，或把 -std 加进 extra_cflags 也会报
  `invalid argument '-std=c++20' not allowed with 'C'`（见
  DRAFT-ohos-cmake-normal-var-shadows-toolchain-standard）——autotools 侧的
  修复形态（CPPFLAGS→CXXFLAGS 拆分）可跨 autotools 库复用，与 CMake 侧不同。

## 恢复条件 / 后续

修复后重跑 `make -j1`；如仍失败，检查是否还有其它 C++ 专用标志（-fmodules-ts、
-fcoroutines 等）泄漏进 CPPFLAGS/CFLAGS，按同法移入 CXXFLAGS。

## 验证命令（可复现）

```bash
grep -n "std=c++" configure.ac src/Makefile.am   # 定位注入点
make -j1 2>&1 | grep "not allowed with 'C'"      # 复现错误
```
