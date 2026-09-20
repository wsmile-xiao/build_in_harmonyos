# DRAFT-yosys-0.66 — 自带 Makefile 自赋 CXX/CC 导致 compiler_executables 失效（产出宿主对象）

## 使用说明

适用对象：在 conan 里适配**自带 Makefile**（非 autotools/cmake/meson）的 C/C++ 项目。
当交叉构建（host 与 build 不同）时，若 Makefile 里写的是 `CC := ...` / `CXX := ...`（不是 `?=`），
conan profile 的 `tools.build:compiler_executables` 不会生效。

处置：在 `self.run` 的**环境前缀**里显式传 `CC=`/`CXX=`，值与 `CXXFLAGS`/`LIBS` 同一方式注入。

```python
compilers = self.conf.get("tools.build:compiler_executables", default={}, check_type=dict) or {}
cc  = 'CC="%s"'  % compilers["c"]   if compilers.get("c")   else ""
cxx = 'CXX="%s"' % compilers["cpp"] if compilers.get("cpp") else ""
self.run('%s %s CXXFLAGS="%s" make -j1 ...' % (cc, cxx, inc), env="conanbuild", cwd=self.source_folder)
```

注意：`CC=`/`CXX=` 走**环境前缀**而不是 make 命令行变量——命令行变量会覆盖 Makefile 自己的
`CXXFLAGS := $(CXXFLAGS) -Wall ... -I.`，把 `-I.` 丢掉（实测报 `kernel/yosys.h not found`）。

## 适用范围

- 构建系统：自带 Makefile（`system: makefile`），且 Makefile 自赋 `CC`/`CXX`
- 阶段：编译通过、链接才失败（因为对象文件已生成，make 不会重编）
- 依赖库为异构架构（如 OHOS aarch64 的 `libtcl8.6.so`）时症状最明显
- 不适用：autotools/cmake/meson（工具链文件天然生效）；Makefile 用 `CC ?=` 且读环境的情况

## 输入输出定义

- 输入：conan profile 的 `tools.build:compiler_executables`（`{"c": ..., "cpp": ...}`）
- 输出：make 进程环境中的 `CC`/`CXX` 前缀；对象文件架构从宿主的 `ELF 64-bit LSB relocatable, x86-64`
  变为目标的 `ARM aarch64`
- 失败信号（链接期）：`/usr/bin/ld: skipping incompatible <dep>/lib/libX.so when searching for -lX`

## 示例

```
$ conan create . -pr:h=ohos-aarch64 -pr:b=default --build=missing
...
[ 26%] Building kernel/driver.o            # 用的是宿主 g++，无报错
...
/usr/bin/ld: skipping incompatible /home/.../tcl/p/lib/libtcl8.6.so when searching for -ltcl8.6
collect2: error: ld returned 1 exit status
```

修复后同一命令：make 命令行里出现 `CC=".../aarch64-unknown-linux-ohos-clang" CXX=".../clang++"`，
链接使用交叉 `ld.lld`，不再报 incompatible。

## 查重差异表（与最相近的既有条目）

| 既有条目 | 相似点 | 本条差异 |
|---|---|---|
| `DRAFT-7324-bglibs-djb-two-stage-cross-build` | 都涉及自带 Makefile 在交叉构建下用错编译器 | 那条是「Makefile 规则把**构建期生成器当目标二进制运行**」，需要两阶段构建；本条是「编译器变量本身被 Makefile 自赋，工具链配置到不了 make」，处置是注入 `CC=`/`CXX=` 环境前缀 |
| `c-sig-3.8-device-download-cache-abs-path` | 都提到 `compiler_executables` | 那条讲 conan 全局配置的字面量展开，与本条的变量覆盖机制无关 |

## 验证证据

命令与原始输出：

```
$ grep -n 'CXXFLAGS' Makefile | head -2
107:CXXFLAGS := $(CXXFLAGS) -Wall -Wextra -Wno-unused-parameter ... -I. -I"$(YOSYS_SRC)"

$ grep -n '^CXX' Makefile | head -2
  CXX = g++            # 自赋，不是 ?=

# 修复后 conan create 的 make 命令行（日志 033-local-create.log）
CC="/home/qianxia/command-line-tools/sdk/default/openharmony/native/llvm/bin/aarch64-unknown-linux-ohos-clang" \
CXX=".../aarch64-unknown-linux-ohos-clang++" CXXFLAGS="-I..." LIBS="-L... -ltcl8.6 ..." \
make -j1 ENABLE_ABC=1 ABCEXTERNAL=... DISABLE_SPAWN=0 TCL_VERSION=tcl8.6

$ file <build>/yosys
ELF 64-bit LSB pie executable, ARM aarch64, interpreter /lib/ld-musl-aarch64.so.1   # RC=0
```

- 退出码：0
- 日志绝对路径：`/mnt/e/dsh working/tasks/yosys-0.66-2026-09-17/logs/033-local-create.log`
- 上游任务：PR #11115（yosys 0.66）
