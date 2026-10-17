# 知识草稿：老代码的 getline() 与 OHOS sysroot 的 POSIX 同名词冲突

| 项 | 值 |
|---|---|
| id | `DRAFT-LEGACY-GETLINE-SYMBOL-CLASH-POSIX2008` |
| trigger_tool | conan / clang / make |
| phase | compilation |
| severity | 2 |
| category | portability / headers / symbol-conflict |
| rec_priority | 1 |
| rec_auto_fix | false |

## 现象

1990 年代的 C 程序在 OHOS aarch64 上交叉编译，`util.c` 直接报：

```
util.c:96:5: error: conflicting types for 'getline'
        int getline(char *s, int n, FILE *f) {
C:/ohos-tc/sysroot/usr/include/stdio.h:155:9: note: previous declaration is here
ssize_t getline(char **__restrict, size_t *__restrict, FILE *__restrict);
```

## 原因

POSIX.1-2008 把 `getline()` 收进了标准库。OHOS 的 musl sysroot 按新标准声明：

```c
ssize_t getline(char **restrict, size_t *restrict, FILE *restrict);
```

而老工程习惯在 `util.c` 里自带同名辅助函数（本例签名是 `int getline(char*, int, FILE*)`，
读一行并把 CR/LF 折叠，返回 `feof`）。两者签名完全不同，同一个翻译单元里默认可见性下
Clang 直接判冲突。

**只在交叉编译时暴露** —— host 用老 glibc 时本机编译常常不报，所以「本地 Linux 编过了」
不能作为证据。

## ⚠ 关键坑：`-D` 宏改名**无效**

直觉做法是编译时加宏改名。实测**行不通**：

```bash
$ clang -Dgetline=mailto_getline -c util.c
util.c:96:5: error: conflicting types for 'mailto_getline'
        int getline(char *s, int n, FILE *f) {
<command line>:2:17: note: expanded from here
#define getline mailto_getline
```

预处理器会同时替换函数**定义处**的标识符，于是 `<stdio.h>` 里的声明也变成
`mailto_getline` —— 冲突只是换了个名字继续报。

**唯一可行**：真改名（改定义处 + 同步调用点），或直接删掉该函数。

## 处置（本例的选择）

选**保留函数体、只改符号名**：

1. 先查该函数是否真被调用 —— 本例 `util.c` 的四个函数（`getword` / `rind` / `getline` /
   `send_fd`）**全部只有定义、没有调用点**，`mailto.c` 从未引用（上游没提供 `util.h`，
   靠隐式声明），所以改完名不存在任何需要同步的调用点。
2. patch 里写明「签名与 POSIX 版本不同（int vs ssize_t，入参形态亦不同），保留函数体
   不改行为」。
3. 没有选择删函数，是为了让评审能一眼判断「行为未变」。

## 三个连锁踩坑（同一次排查里遇到，一并记录）

### 1. conandata.yml 的 `patches` 必须用**列表**格式，否则补丁被静默跳过

这是本次最贵的一个坑，因为它**双重误导**。

一开始把 conandata 写成 dict-by-filename：

```yaml
# ❌ 错误
patches:
  0001-rename-getline-to-avoid-posix-sysroot-clash.patch:
    patch_file: "patches/0001-rename-getline-to-avoid-posix-sysroot-clash.patch"
```

Conan 2.x 的 `apply_conandata_patches()` 按 `self.version` 去查
`patches.get(version)` —— key 是文件名时取到**空列表**，补丁被**静默跳过、
不报任何错**。现象是「补丁明明写了却没生效，编译错误仍是原来的
`conflicting types`」。

**误导路径**：第一反应是「`apply_conandata_patches()` 在本环境下坏了」，
于是绕道改成手工 `self.run("patch -p1 --batch -i ...")` —— 本地确实编过了，
但**同时踩中 CI 门禁 L0f**（该门禁专验 conandata 的 patches 格式）：

```
[fail] L0f: conandata.yml patches format wrong —
       key '0001-...patch' is a filename, not a version
       Use list format (recommended):
         patches:
           - patch_file: "patches/0001-...patch"
             patch_description: "..."
             patch_type: "portability"
L0_RESULT=fail: gate failed: bad_patch_format
L1_RESULT=skip: blocked_by_L0
```

**正确格式**（`docs/ADAPTATION_GUIDE.md` 第 7 节）：

```yaml
patches:
  - patch_file: "patches/0001-rename-getline-to-avoid-posix-sysroot-clash.patch"
    patch_description: "..."
    patch_type: "portability"
```

**教训**：工具「静默失败」比「报错」危险得多。遇到"配置了却没生效"，
第一反应应该是**怀疑配置的格式/语义**，而不是先怀疑工具坏了。

### 2. 手写 unified diff 的 `@@` 行数不准 → `patch` 报 malformed 且静默不生效

手写 patch 头 `@@ -93,7 +93,20 @@` 时，只要实际增删行数对不上，GNU patch 会：

```
patch: **** malformed patch at line 17: ...
```

**处置**：
- 用 `difflib.unified_diff(..., n=3)` 从真实原文自动生成，不要手写行数
- 改完 conanfile 记得清缓存：`conan remove "<pkg>/<ver>:*" -c`，
  否则 conan 会复用旧 build 目录里的未打补丁源码

### 3. 断言必须来自实测输出，不能来自读源码

最初按源码里的注释块写了断言 `Version 1.3.2`。qemu 真机跑出来其实是：

```
mailto v1.3.2
(c) 1994-1998 by Andreas Ley (Andreas.Ley@rz.uni-karlsruhe.de)
```

那段 `** Version 1.3.2 - 2.3.1999` 是 **C 注释**，根本不会被打印。

**处置**：所有 CLI 断言都必须先在 qemu-aarch64 + OHOS sysroot 下抓一次真实输出，
再照抄。本例据此把用例从 4 条扩到 17 条，并补上「裸调用输出 CGI 表单」这个更强的断言
（`Content-type: text/html` + `<TITLE>WWW Mail Gateway</TITLE>`）。

## 推广：还有哪些名字会撞

同机制的可检索名单（老 libc 从未提供、POSIX.1-2008 新增）：

```
getline  getdelim  mempcpy  strndup  strcasestr  rawmemchr  fgetws
```

以及历史遗留的 BSD 名字（某些 libc 仍有声明）：

```
index  bcopy  bcmp  random  srandom  wait3
```

## 快速自查命令

```bash
grep -nE '^\s*(int|ssize_t|char\s*\*)\s+(getline|getdelim|mempcpy|strndup|rawmemchr|index|bcopy|random)\s*\(' *.c
qemu-aarch64 -L <ohos-sysroot> ./a.out -v
```
