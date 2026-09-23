# DRAFT: conan 交付链两处「静默失败」陷阱

> 草稿编号：DRAFT-conan-delivery-chain-silent-traps（待审核 promote）
> 来源：dasm 2.20.15-202011092.20.14.1 适配（本包实际踩中陷阱一并修复），2026-09-10
> 路径 B（知识库扩展）素材

两处陷阱的共同点：**在 glibc/常规工作流上完全正常，出问题时既不报错、也不影响
`conan create` 的退出码**。编译日志与 CI 状态都查不出来，只能靠实物核对或主动用
严格方言编一遍才能发现。

---

## 陷阱一：`conan.tools.files.copy()` 的 pattern 是「相对 src 的路径」fnmatch

### 现象

`conan create` 退出码 0、构建日志全绿、`Built target test_xxx` 正常打印，
但打开包目录发现 **`bin/` 根本不存在**。

### 根因

```python
copy(self, "dasm", src=self.source_folder, dst=bin_dst)   # ← 静默零拷贝
```

`copy(conanfile, pattern, src, dst, keep_path=True)` 把 pattern 与**相对 `src`
的路径**做 fnmatch，**不与 basename 匹配**。以 `source_folder` 为 `src` 时，
产物的相对路径是 `bin/dasm`：

```python
fnmatch("bin/dasm", "dasm")   # False → 一个字节都不拷，且不报错
```

### 正确写法

让「相对 `src` 的路径」恰好等于 pattern：

```python
src = os.path.join(self.source_folder, "src")     # 产物就在这一层
copy(self, "dasm", src=src, dst=bin_dst)
copy(self, "ftohex", src=src, dst=bin_dst)
```

### 对照理解该语义

| 写法 | 结果 | 原因 |
|---|---|---|
| `copy(self, "*", src=<sf>/machines, dst=…)` | 正常 | `*` 能匹配含 `/` 的相对路径 |
| `copy(self, "dasm.txt", src=<sf>/docs, dst=…)` | 正常 | 文件就在 docs 顶层 |
| `copy(self, "dasm", src=<sf>, dst=…)` | **静默零拷贝** | 相对路径是 `bin/dasm`，不匹配 |

**规律：pattern 不含 `/` 时，`src` 必须至少深入到产物所在的那一层。**

### 唯一的发现手段：包目录实物核对

```console
$ conan create <dir> -pr:h=ohos-aarch64 -pr:b=default
$ conan cache path <ref>:<pkgid>          # 注意要带 :<pkgid>，否则只给 export 目录
$ ls -R <该目录>                           # 逐项核对预期文件
```

配合 test_package 的安装布局断言（`access(pkg/bin/x, X_OK)`），可以把这类
"成功产出的坏包"挡在 CI 里。

---

## 陷阱二：`-std=c99` 下 `popen`/`pclose` 声明被隐藏 → 指针截断 → 运行时段错误

### 现象

```console
warning: implicit declaration of function 'popen'
warning: initialization of 'FILE *' from 'int' makes pointer from integer without a cast
```

编译**通过**（仅告警），运行直接段错误：

```console
Segmentation fault (core dumped)   # 实测 glibc 2.35：exit 139
```

### 根因

`popen`/`pclose`/`access`/`WIFEXITED` 都是 POSIX 而非 ISO C。在**严格 ISO C**
方言下（显式 `-std=c99`/`-std=c11`，未定义 `_POSIX_C_SOURCE`），**glibc 与 musl
都会隐藏 `popen`/`pclose` 的声明**。缺声明时编译器按隐式 `int` 处理，
`FILE *fp = popen(...)` 把 int 截断成指针 → 崩。

### 为什么很难自己发现

**CMake 默认用 gnu 方言，不暴露该问题**：gnu 方言下 `_DEFAULT_SOURCE` 自动定义，
声明齐全。只有本地刻意加 `-std=c99` 单独编一遍才会现形——而 CI 用的正是 CMake
默认方言，于是"本地全绿、线上也全绿"，直到某次有人用严格方言编译。

### 修法

放在 test 源文件**所有 `#include` 之前**：

```c
/* ★ 特性测试宏必须在所有 #include 之前 */
#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#endif

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>
```

### 建议固化为提交前自检动作

```console
$ cc -std=c99 -Wall -Wextra -I<test_package> <test_package>/test_x.c -o /tmp/t
```

这一步同时能抓出隐式声明与 `-Wformat-truncation` 一类的格式截断问题。

---

## 附带：上游测试套件里「双登记」用例的复核顺序陷阱

上游 harness（如 dasm 的 `test/run_tests.sh`）常分 strict=off / strict=on 两段，
部分用例**同时**登记：

- `<name>.bin.ref` —— 非 strict 段期望汇编成功且产物逐字节匹配；
- `<name>.fail` —— strict 段加 `-S` 期望报错，并校验期望错误码。

strict 段会把同名 `<name>.bin` **清空为 0 字节**。因此：

- 先跑 strict 段、再 `cmp name.bin name.bin.ref` → 必然 mismatch，
  **容易误判为"真值写错了"**；
- 正确做法：逐字节复核必须在**非 strict 段之后单独重跑**目标用例。

本次 dasm 实测正是如此：`doublemacro` 一度显示 mismatch，单独重跑后产物
`00 F8 A9 01` 与 `.bin.ref` **完全一致**。

---

## 验证证据（dasm 实测）

| 项 | 结果 |
|---|---|
| 配方构建（OHOS clang，`conan create`） | 通过；修复前包内无二进制（陷阱一） |
| 包目录实物核对 | `bin/dasm` 203552 B、`bin/ftohex` 16720 B，均为 ELF64 AArch64 PIE |
| test_package（真实 OHOS aarch64 制品实跑） | **38 passed, 0 failed** |
| 严格方言自检 | 修复前 exit 139（陷阱二）；修复后 38/38 |
| 上游套件 | 93 例 85 OK（8 项均上游既有元测试/既知失败） |

相关但独立的 musl API 缺口见 `DRAFT-ohos-musl-strlcat-strlcpy-gap-bridge`。
