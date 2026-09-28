# Draft: Raw-Makefile 顶层 `CC = gcc` 硬赋值 + 字面 `ar rcs` 在 Conan 工具链环境下失效（OHOS clang-only）— 改为 `?=` 与 `$(AR)`

> Source event: `libconfigini/22d700ab76` first OHOS adaptation on 2026-09-27.
> Draft only. Do not promote to `knowledge/graph/` without reviewer assignment.
> Same-stem pair: `DRAFT-makefile-toolchain-vars-equals-hardcode.kv` / `.md`

## Problem

`libconfigini` 22d700ab76 是纯 Makefile C 库（无 configure），顶层 Makefile 硬编码：

```makefile
CFLAGS = -g -Wall -Wno-char-subscripts
CC = gcc
...
$(LIBARCH): $(OBJS)
	ar rcs $(LIBARCH) $(OBJS)
```

OHOS PC 工具链只提供 clang/llvm-ar（无 gcc、无 binutils `ar`）。由于 `=` 是硬赋值，
Conan 通过 AutotoolsToolchain 生成的 `conanbuild` 环境注入的
`CC=clang / CFLAGS=... / AR=llvm-ar` **压不过 Makefile 的 `=` 赋值**，
`conan create` 内构建仍调用 gcc / 字面 `ar` → 失败
（本任务实际呈现：`make: gcc: No such file or directory` 家族错误 / 归档命令无法使用工具链 ar）。

## Why the usual workarounds fail

- `make CC=clang` 命令行覆盖对 `=` 赋值**有效**，但 R33 禁止手写 shell 变量注入编译器，
  且 `conan create` 的复现构建不依赖命令行参数——不可作为配方方案。
- `AR=llvm-ar` 环境变量（E012 方案）只对 Makefile 中 **使用 `$(AR)` 变量** 的归档规则生效；
  字面 `ar rcs` 直接忽略环境变量。
- 与 cnrbtree 草稿的区别：cnrbtree 是 recipe 内嵌 gcc（**无 CC 变量**），需把 recipe 重写为
  `$(CC)`；本候选是**顶层有 CC 变量但用 `=` 硬赋值**（有变量，赋值方式错），
  且额外包含字面 `ar rcs` 归档命令（E012 env 方案失效的边界）。

## Fix

用最小补丁把硬赋值改为条件赋值、字面归档命令改为变量引用：

```diff
-CC = gcc
+CC ?= gcc

-CFLAGS = -g -Wall -Wno-char-subscripts
+CFLAGS ?= -g -Wall -Wno-char-subscripts

-	ar rcs $(LIBARCH) $(OBJS)
+	$(AR) rcs $(LIBARCH) $(OBJS)
```

Conan 配方侧：`AutotoolsToolchain.generate()`（产生 conanbuild env）→
`self.run("make -j1 all", env="conanbuild")` + `make -j1 test`（上游测试），
`make installdir=<pkg> install`（安装头文件与静态库）。

补丁文件注意点：上游 Makefile 若为 CRLF 行尾，生成的 `.patch` 必须保持 LF 行尾、
hunk 行号/计数正确且文件尾部有换行，conan 的 patch_ng（`apply_conandata_patches`）
才能解析应用（CRLF 补丁会报 `patch stream is incomplete`）。

## Verification

```bash
conan create . -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
# rc=0；libconfigini.a 构建成功；test_package 2/2 CTest PASS（消费者 test.c + 鸿蒙专项 test_ohos.c）
make -j1 test   # 上游 Test1..Test4 rc=0
# conan-verify G0-G4/L2/L4/L5 pass；W3 build_and_test.sh RC=0
```

## Applicable boundary / counterexample

- 适用：顶层 Makefile 用 `=` 硬赋值 CC/CFLAGS 且归档命令字面 `ar` 的纯 Makefile C/C++ 库。
- 不适用/反例：configure 阶段（走 E001/E007 通道）；Makefile recipe 内嵌编译器无变量
  （走 cnrbtree 草稿，recipe 重写为 `$(CC)`）；Makefile 已用 `?=`/变量且无字面 ar
  （cohomcalg 草稿，命令行覆盖即可，无需补丁）。
