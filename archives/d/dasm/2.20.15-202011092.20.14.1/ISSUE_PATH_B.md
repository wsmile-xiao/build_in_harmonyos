# 路径 B 知识库扩展申请：OHOS(musl) 缺 `strlcat`/`strlcpy` 的补桥模式，及两处**静默失败**的交付链陷阱

## 申请信息

- **申请类型**：路径 B（知识库扩展，10 分候选）
- **关联任务**：#6992 dasm `2.20.15-202011092.20.14.1`
- **关联 PR**：`!` feats/dasm （`feat/dasm-2.20.15-202011092.20.14.1`，配方 PR）
- **知识草稿**：`knowledge/drafts/DRAFT-ohos-musl-strlcat-strlcpy-gap-bridge.kv` / `.md`、
  `knowledge/drafts/DRAFT-conan-delivery-chain-silent-traps.kv` / `.md`
- **提交方式**：草稿与配方归档**同一原子 PR 分支**提交
- **申请日期**：2026-09-10

## 一、为什么这是"可跨仓库复用的知识"

本条给出三类问题，共同点是**在 Debian/glibc 上完全正常，换到 OHOS 上就"静默"出问题**——
其中两类的失败形态**不报错**（零拷贝、只在运行时崩），靠编译日志查不出来：

1. musl 缺失 BSD 血统的 `strlcat`/`strlcpy`（**新代码高发**）；
2. `conan.tools.files.copy()` 的 pattern 语义误用导致 **package() 静默零拷贝**；
3. 严格 ISO C 方言下 POSIX 函数声明被隐藏，`FILE *fp = popen(...)` **运行时段错误**。

## 二、前提：`strlcat`/`strlcpy` 不是 C 标准库的"必然存在物"

| libc | `strlcat`/`strlcpy` |
|---|---|
| OpenBSD / FreeBSD / macOS | 原生提供 |
| glibc | **2.38（2023-08）起**才纳入 |
| **OHOS musl** | **没有** |

判据（一条命令即可在适配前定性）：

```console
$ grep -rn '\bstrlcpy\b\|\bstrlcat\b' src/ | grep -v '^src/.*\.o'
$ echo '#include <string.h>
size_t f(char*d,const char*s,size_t n){return strlcat(d,s,n);}' > t.c && clang -std=c99 -c t.c
# → implicit declaration（clang 15+ 默认按错误处理）；不隔离则链接期 undefined reference
```

dasm 的 `src/errors.c` 在 `append_level` / `append_location` / `append_information`
**三处无条件调用 `strlcat()`**，项目内没有任何自带实现——它默认"libc 一定有"，
这正是 2018-2020 年代代码的普遍假设（glibc 那时还没有，但 BSD/macOS 有，
作者多在 macOS 上开发）。

**补桥模式（配方侧 shim，不改上游源码、不删调用）：**

```c
/* 经 -include 前置到每个编译单元之前 */
#include <stddef.h>
size_t dasm_compat_strlcat(char *dst, const char *src, size_t siz);
size_t dasm_compat_strlcpy(char *dst, const char *src, size_t siz);
#define strlcat dasm_compat_strlcat
#define strlcpy dasm_compat_strlcpy
```

两个设计要点：

- **用宏改名，不用条件声明**：在已提供 `strlcat` 的 libc 上，`<string.h>` 里的原型
  会被一并改名成**同签名**的自带实现，不会重复定义；在 musl 上则同时给出声明与实现。
  若改用 `#if !defined(__GLIBC__)` 之类的条件判断，反而要枚举所有 libc。
- **必须严格复刻 OpenBSD 返回值语义**：截断时返回"拼接所需的完整长度"而非"已写长度"。
  dasm 的 `errors.c` 把该返回值当已写长度继续推进，用 `strncat` 凑会算错偏移。

实测确认（aarch64 制品）：

```console
$ nm -D pkg/bin/dasm | grep strl
                 U strlen
0000000000016c24 T dasm_compat_strlcat     ← 自带实现，动态符号表无 UND strlcat
$ readelf -d pkg/bin/dasm | grep NEEDED
 0x0000000000000001 (NEEDED)  Shared library: [libc.so]
```

## 三、陷阱一：`conan.tools.files.copy()` 的 pattern 是「相对 src 的路径」fnmatch

这是本包实际踩到并导致**包目录里没有二进制**的一次。第一版写法：

```python
copy(self, "dasm", src=self.source_folder, dst=bin_dst)   # ← 静默零拷贝
```

`copy()` 把 pattern 与**相对 src 的路径**做 fnmatch，不与 basename 匹配。以
`source_folder` 为 src 时产物相对路径是 `bin/dasm`：

```python
fnmatch("bin/dasm", "dasm")   # False
```

结果：**一个字节都不拷、不报错、不告警**，`package_folder/bin/` 直接不存在。
只有 test_package 的 `access("<pkg>/bin/dasm", X_OK)` 断言能发现。

正确写法（让相对路径恰好等于 pattern）：

```python
src = os.path.join(self.source_folder, "src")
copy(self, "dasm", src=src, dst=bin_dst)
```

对照：`copy(self, "*", src=<sf>/machines, dst=...)` 之所以正常，是因为 `*` 能匹配
含 `/` 的相对路径；`copy(self, "dasm.txt", src=<sf>/docs, dst=...)` 正常是因为
文件就在 docs 顶层。**规律：pattern 不含 `/` 时，src 必须至少深入到产物所在的那一层。**

排查动作（建议作为配方自检项）：`conan create` 后用
`conan cache path <ref>:<pkgid>` 打开包目录，逐项核对预期文件是否真的落地。

## 四、陷阱二：`-std=c99` 下 `popen`/`pclose` 声明被隐藏，指针截断 → 运行时段错误

test_package 里用 `popen`/`pclose` 直读子进程输出是主流写法。但在**严格 ISO C**
方言下（显式 `-std=c99`，未定义 `_POSIX_C_SOURCE`），**glibc 与 musl 都会隐藏
`popen`/`pclose` 的声明**：

```console
warning: implicit declaration of function 'popen'
warning: initialization of 'FILE *' from 'int' makes pointer from integer without a cast
→ 编译通过（仅告警），运行时段错误（实测 glibc 2.35：exit 139）
```

这个陷阱的隐蔽性在于：**CMake 默认用 gnu 方言不暴露它**（gnu 方言下
`_DEFAULT_SOURCE` 自动定义），只有在本地刻意加 `-std=c99` 编一遍才会现形。

修法（放在 test 源文件所有 `#include` 之前）：

```c
#ifndef _POSIX_C_SOURCE
#define _POSIX_C_SOURCE 200809L
#endif
```

建议：把「本地用 `-std=c99 -Wall -Wextra` 单独编一遍 test_package」作为提交前自检动作，
它能同时抓出隐式声明与格式截断类问题。

## 五、附带：上游测试套件里"双登记"用例的复核陷阱

dasm 的 `test/run_tests.sh` 分 strict=off / strict=on 两段，部分用例**同时**登记
`<name>.bin.ref`（非 strict 段期望汇编成功且产物匹配）与 `<name>.fail`（strict 段
加 `-S` 期望报错并校验期望错误码）。

strict 段会把同名 `<name>.bin` **清空为 0 字节**。因此顺序敏感：

- 先跑 strict 段、再做 `cmp name.bin name.bin.ref` → 必然 mismatch，**误判为真值错误**；
- 正确做法是逐字节复核必须在**非 strict 段之后单独重跑**目标用例。

本包实测（WSL/Ubuntu 22.04 + gcc 11.4 复刻配方构建）：

```console
executed 93 tests, 85 OK, 8 failed
```

8 项未通过**全部是上游既有状态**：7 项在 `selftest/` 元测试目录（故意制造失败以验证
harness 能识别失败），1 项是 `atari7800/spritesample`（上游 Makefile 头部已注明既知
不编译）。上游 `make test` 自己也会打印 "testing is not fully automated yet"。

## 六、验证证据

| 项 | 结果 |
|---|---|
| 配方构建（OHOS clang，`conan create`） | 通过，test_package 编译成功 |
| `bin/dasm` | 203552 B，ELF64 AArch64 PIE，`NEEDED` 仅 `libc.so` |
| `strlcat` | 由 `dasm_compat_strlcat` 提供，无 UND strlcat |
| test_package | **38 passed, 0 failed**（在真实 OHOS aarch64 制品上实跑） |
| 上游套件 | 93 tests, 85 OK, 8 failed（8 项均上游既有） |

`test_package` 的 38 项包含 12 个上游用例的**逐字节**回归比对（origin 头 + 机器码，
真值直接取自上游 `test/*.bin.ref`）、`ftohex` 的 Intel HEX 往返、用法横幅与
`ERROR_COMMAND_LINE(1)` 退出码，以及随包机器头/手册页的安装断言。

## 七、同时提交的两份草稿

1. `DRAFT-ohos-musl-strlcat-strlcpy-gap-bridge.kv/.md`
   —— musl 缺失 BSD API 的识别与补桥模式（**与 argp/musl-fts/musl-obstack 同族**，
   属"glibc 有、musl 无"补齐家族的新成员）；
2. `DRAFT-conan-delivery-chain-silent-traps.kv/.md`
   —— 交付链两处静默失败：`copy()` 相对路径 fnmatch 零拷贝、严格 ISO C 隐藏 POSIX
   声明导致运行时段错误（含双登记用例的复核顺序陷阱）。
