# DRAFT-dmc_unrar-1.8.0-single-file-c-direct-compile：零构建系统单文件 C 库（stb 风格）的 Conan 直编配方

> Contributor: AtomCode | Status: Draft | Updated: 2026-09-21
> Source: dmc_unrar 1.8.0 适配（上游仅 COPYING/README/dmc_unrar.c/example.c，无任何构建系统）
> 对应：`knowledge/drafts/DRAFT-dmc_unrar-1.8.0-single-file-c-direct-compile.kv`

## 现象

适配 stb 风格单文件 C 库（如 dmc_unrar：一个 `.c` 内同时含头文件声明与实现）时：

1. `conan-init` 按 URL 猜测构建系统生成 **autotools 模板**，但上游根本没有
   configure/Makefile/CMake/meson，模板完全不适用；
2. 手写 build() 直接编译时报：
   ```console
   clang-15: error: no such file or directory: 'dmc_unrar.c'
   clang-15: error: no input files
   ```
3. 包体需要头文件，但库没有单独 `.h` —— 头与实现都在 `dmc_unrar.c` 里。

## 根因

- `basic_layout()` 把源码解压到 `build/src`（`self.source_folder`），而 `build()`
  默认 cwd 是 `self.build_folder`，用相对路径 `dmc_unrar.c` 编译必然找不到；
- 单文件库的"头"就是 `.c` 的前半段，上游约定通过定义
  `DMC_UNRAR_HEADER_FILE_ONLY` 再 include 来只取声明部分
  （实现段由 `#ifndef DMC_UNRAR_HEADER_FILE_ONLY` 守卫）。

## 修复（已验证）

**build()（custom 直编，R33 合规）**：
```python
cc = self.conf.get("tools.build:compiler_executables", default={}).get("c", "cc")
src = os.path.join(self.source_folder, "dmc_unrar.c")
obj = os.path.join(self.build_folder, "dmc_unrar.o")
self.run(f"{cc} -O2 -c {src} -o {obj}")          # 绝对路径！
self.run(f"ar rcs libdmc_unrar.a {obj}")         # shared 时 -fPIC + -shared
```

**package()（头/实现分离）**：
- `include/dmc_unrar.c`：安装原文件（支持上游 stb 风格整体内联）；
- `include/dmc_unrar.h`：生成的包装头——
  ```c
  #ifndef DMC_UNRAR_HEADER_FILE_ONLY
  #define DMC_UNRAR_HEADER_FILE_ONLY
  #endif
  #include "dmc_unrar.c"    /* 只出声明，实现来自 libdmc_unrar */
  ```
- `lib/libdmc_unrar.a`、`licenses/COPYING`。

**package_info()**：`self.cpp_info.libs = ["dmc_unrar"]`。

消费者两种用法自由选择：`#include <dmc_unrar.h>` + 链接库（声明+链接），或
`#include "dmc_unrar.c"`（上游整体内联风格）。

## 验证

dmc_unrar 1.8.0：conan-verify G0-G4/L2/L4/L5 全 PASS；test_package 消费者用例 1/1
（内嵌 RAR5 夹具，真实 API 调用 + 解压字节数校验）；独立消费者程序链接已安装
lib+头运行 ALL PASSED（2×2048B 文件解压一致）。

## 适用边界

- 仅适用于**无任何构建系统**的单文件/极简 C 库；
- 有 Makefile 的 raw-makefile 项目走 E392 三要素（get() filename / compiler
  executables dict / make cwd）；
- 纯 header-only（无编译产物）走 E035；
- 本条是"无构建系统 + 需编译出库"的中间态，三者互补不冲突。