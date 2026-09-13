# E570 — OHOS libc 缺少 BSD 遗留别名 rindex：nm 预检与 strchr/strrchr 等价改写

> Contributor: EB2A | Status: Draft | Updated: 2026-09-11
> Source: dazzdb 1.0-git20250217.a3eefd4 适配（设备单端，clang 15.0.4 / ohos-sdk 26.0.0.18）

## 错误特征

上游 C 代码调用 BSD 遗留别名 `index()`/`rindex()` 时，OHOS 上先出现编译期提示、再在链接期硬失败：

```
DB.c:117:15: warning: call to undeclared library function 'rindex' with type 'char *(const char *, int)';
              ISO C99 and later do not support implicit function declarations [-Wimplicit-function-declaration]
  if ((find = rindex(name,'/')) != NULL)
              ^
DB.c:117:15: note: include the header <strings.h> or explicitly provide a declaration for 'rindex'
1 warning generated.
ld.lld: error: undefined symbol: rindex
>>> referenced by DB.c
>>>               /storage/Users/currentUser/DB-210a39.o:(PathTo)
>>> referenced 5 more times
>>> did you mean: index
>>> defined in: .../sysroot/usr/lib/aarch64-linux-ohos/libc.so
```

关键点：**链接器给出的候选是 `index`**——同一个头、同一个 BSD 别名族，一个在、一个不在。
clang 15 只把隐式声明当警告，所以只有链接期错误是硬信号。

## 触发条件

- 构建系统: 任意（实测 raw makefile）
- 阶段: compilation（警告）→ linking（错误）
- 前提: 源码直接调用 `rindex()`（或 `index()`），且未自带等价实现

## 根因分析

`index()`/`rindex()` 是 BSD 的 `strchr()`/`strrchr()` 别名，POSIX 只标准化后者。OHOS 的
libc 在这个别名族上**不对称**：

```bash
$ nm -D --defined-only $SYSROOT/usr/lib/aarch64-linux-ohos/libc.so | grep -E ' (index|rindex)$'
0000000000011d80 T index
# rindex 无输出
```

因此：

1. 编译期 `rindex` 无声明（OHOS 的 `strings.h` 不声明它），clang 15 按 C99+ 规则只警告；
2. 链接期符号不存在，`ld.lld` 直接失败；
3. **符号确实不存在，所以特性宏救不回来**：即使显式 `#define _GNU_SOURCE` 并包含 `<strings.h>`，
   警告与链接错误都原样保留（见下节反证）——这一点把它与 E032（`_BSD_SOURCE`→`_GNU_SOURCE`
   的 dirent 可见性）和 E093/E094（GNU 扩展函数缺失但可由等价实现兜底）区分开。

## 可复用方案

### 1. 先做符号表预检（10 秒，避免走弯路）

```bash
SYSROOT=<ohos-sdk>/native/sysroot
nm -D --defined-only $SYSROOT/usr/lib/aarch64-linux-ohos/libc.so | grep -E ' (index|rindex)$'
```

任何老 C 代码在 OHOS 上的首次链接失败，都建议先跑一遍"遗留别名族"探测：`index`/`rindex`、
`bzero`/`bcopy`/`bcmp`、`strcasecmp` 等。符号表是唯一可信依据，不要用 musl 的先验知识代替。

### 2. 统一改写为 POSIX 等价函数

```bash
# 设备端 /bin/sed 是 toybox：\b 词边界等 GNU 扩展静默失效，只用字面串并复核替换计数
sed -i 's/rindex(/strrchr(/g' DB.c DB2ONE.c DBshow.c
grep -c 'strrchr(' DB.c DB2ONE.c DBshow.c   # 替换计数必须与预期一致
grep -c 'rindex('  DB.c DB2ONE.c DBshow.c   # 必须为 0
```

`strchr`/`strrchr` 由 `<string.h>` 声明（本族项目普遍已包含），无需特性宏、无需平台条件编译，
语义与返回值完全等价。改写后按普通补丁流程落 `patches/`。

### 不在方案空间内的做法

- ❌ 补 `extern char *rindex(...)` 或平台条件编译：只消除警告，链接期照样 undefined；
- ❌ 只改 `rindex` 而不断言 `index` 的可见性：两个别名在本平台的可见性不对称，须按实测符号表走；
- ❌ 依据"musl 两个别名都提供"的先验直接下结论。

## 验证

```bash
# 修复前（上游原样）：第一条真实错误
clang -O3 -Wall -Wextra -Wno-unused-result -fno-strict-aliasing -o /dev/null fasta2DB.c DB.c QV.c -lm
#   -> ld.lld: error: undefined symbol: rindex / did you mean: index

# 修复后：21 个目标全部构建成功且无 rindex 引用
make -j1 CC=$OHOS_CLANG
nm -D <构建产物> | grep -c rindex    # 0
```

## 与既有条目的差异（含实测反证）

| 既有条目 | 覆盖点 | 与本条目的差别 |
|----------|--------|----------------|
| E032 | `_BSD_SOURCE` → `_GNU_SOURCE` 修复 dirent API 可见性 | 那类问题的**符号是存在的**，改特性宏即可；本条目符号不存在，改宏无效——见下方反证 |
| E093 | musl 缺 `getpass()`（GNU 扩展）；其 `error_signature` 同时覆盖编译期 `implicit declaration of function.*getpass` 与链接期 `undefined reference to.*getpass` | 同属"缺函数→等价改写"族，但 E093 的落点是"函数缺失，可用 `fgets` 等价实现替换语义"；本条目是**同族别名可见性不对称**（`index` 在、`rindex` 不在），改写目标是**语义完全相同的另一个 POSIX 函数**，且特性宏完全无效（见下方反证） |
| E094 | musl 缺 `pthread_attr_setaffinity_np`；其 `rec_command` 实际给的是 `#ifndef __OHOS__` 条件编译跳过调用，不是等价实现 | 与本条目的差别更明显：E094 属"能力不可用→按平台条件跳过"，本条目**不引入任何平台条件编译**，只是把调用点换成等价的 POSIX 函数（对 Linux 同样正确） |

**反证（实测，2026-09-11，OHOS 设备）**——特性宏不能替代改写：

```c
// rindex_gnu.c
#define _GNU_SOURCE
#include <strings.h>
#include <stdio.h>
int main(void) { printf("%s\n", rindex("a/b", '/') + 1); return 0; }
```

```bash
$ clang -Wall -o rindex_gnu rindex_gnu.c
rindex_gnu.c:4:33: warning: call to undeclared library function 'rindex' ... [-Wimplicit-function-declaration]
rindex_gnu.c:4:33: note: include the header <strings.h> or explicitly provide a declaration for 'rindex'
1 warning generated.
ld.lld: error: undefined symbol: rindex
```

即使定义了 `_GNU_SOURCE` 且包含了 `<strings.h>`，OHOS 既不声明也不导出 `rindex`；
而 E032 型的 `_BSD_SOURCE` 问题在同一工具链下改宏即生效（符号存在）。两者不可互换。

**A/B 对照（符号表）**：

```bash
$ nm -D --defined-only $SYSROOT/usr/lib/aarch64-linux-ohos/libc.so | grep -cE ' T index$'   # 1
$ nm -D --defined-only $SYSROOT/usr/lib/aarch64-linux-ohos/libc.so | grep -cE ' T rindex$'  # 0
```

## 关联条目

- 相似: E093（musl 缺 GNU 扩展函数 getpass）、E094（musl 缺 pthread_attr_setaffinity_np）
- 相似但机制不同: E032（`_BSD_SOURCE`/`_GNU_SOURCE` 可见性，符号存在）
- 实测来源: dazzdb 1.0-git20250217.a3eefd4（`patches/0002-replace-BSD-rindex-with-POSIX-strrchr.patch`）

## 落地证据

- 受影响调用点：`DB.c` 5 处、`DB2ONE.c` 2 处、`DBshow.c` 2 处（共 9 处）
- 修复后 21 个可执行产物全部构建成功，适配侧 93 项断言全通过（`conan create` 内 `test_package` 实跑）
- 该错误是"Makefile 硬编码 gcc"修复后暴露的第一条**真实**链接错误，符合最小改动定位顺序
