# cvs-fast-export 1.59 适配笔记

## 上游信息
- 上游: Eric S. Raymond（esr）的 cvs-fast-export
- 功能: 把 CVS/RCS 仓库高速导出为 `git fast-import` 流（CVS→git 迁移工具）
- 形态: 手写 Makefile，22 个目标文件 + 3 个 Python 辅助脚本（cvsconvert/cvsstrip/cvssync）

## 源码获取
```
https://deb.debian.org/debian/pool/main/c/cvs-fast-export/cvs-fast-export_1.59.orig.tar.gz
sha256 = 2439cd83f54c98f248e85d3ba3becbe028580e89652c50756022fbe564a9e8da
```

## 编译要点（四处与上游 Makefile 的契约落差）

### 1. 不用 bison/flex —— 直接用随包生成的 .c

tarball 里**同时**有生成产物与其源：

```
gram.c  gram.h   ← 由 gram.y 生成
lex.c   lex.h    ← 由 lex.l 生成
```

而 Makefile 有再生成规则：

```make
gram.h gram.c: gram.y
	$(BISON) $(YFLAGS) --defines=gram.h --output-file=gram.c $(srcdir)/gram.y
lex.h lex.c: lex.l
	$(FLEX) $(LFLAGS) --header-file=lex.h --outfile=lex.c $(srcdir)/lex.l
```

一旦 `.y/.l` 时间戳比 `.c` 新（解包顺序、文件系统精度都可能造成），`make` 就会调
`bison`/`flex` —— **CI 没有这两个工具**。绕过 make 直编时直接用随包的 `gram.c`/`lex.c`，
把 bison/flex 彻底排除在构建依赖之外。

### 2. 混合 make 方言

Makefile 同时使用 BSD make（`.PATH`、`.PARSEDIR`、`?=`）与 GNU make（`$(shell …)`），
还带 `VPATH`/`srcdir` 计算。直接驱动 clang 可绕开全部方言问题。

### 3. 版本号是「从文档抽取 + 字符串字面量宏注入」

```make
VERSION=$(shell sed -n <NEWS.adoc '/::/s/^\([0-9][^:]*\).*/\1/p' | head -1)
CPPFLAGS += -DVERSION=\"$(VERSION)\"
```

`main.c: printf("%s: version " VERSION "\n", argv[0]);` —— 宏未定义即语法错误。
配方**生成内联头文件 `_cfe_version.h` 用 `-include` 注入**（`#define VERSION "1.59"`），
既复刻了宏，又避开 `-DVERSION=\"...\"` 在 cmd.exe 与 POSIX sh 下的引号差异。
（`VERSION` 的实际取值从 `NEWS.adoc` 首个含 `::` 的行读出 = `1.59`。）

### 4. 多线程开关必须保留

```make
CFLAGS += -pthread
CPPFLAGS += -DTHREADS
```

上游默认开启（collate 阶段并行）。配方同样传 `-pthread -DTHREADS`，
保证行为与上游一致。

另：源码以 `#include "cvs.h"` 形式同目录引用，需 `-I.`。

## 运行验证
- `cvs-fast-export -V` → `<argv0>: version 1.59`（main.c 的确切输出）
- `cvs-fast-export -h` → `Usage: cvs-fast-export [OPTIONS] [FILE]...`（main.c 的确切输出）
- 真实仓库转换需要 cvs/cvsps 与真实 RCS 夹具，不在本 PR 范围。

## 测试（test_package，9 条断言）
1. `bin/cvs-fast-export` 存在 + 可执行
2. ELF64 / AArch64（`e_machine == 0xB7`）
3. `-V` 真实执行（未被信号杀死、未落在 126/127/128+）且输出含 `version`
4. `-h` 真实执行（同判据）且输出含 `Usage`
5. `cvsconvert` / `cvsstrip` / `cvssync` 三个脚本存在且可执行

assertion_count = 9（上游可自动化项为 0 —— `tests/` 需要 cvs/cvsps/git 与 RCS 夹具）。

### 判据加固（P2/P3）
- **P2**：`popen` 经 `/bin/sh` 中转，被信号杀死的子进程由 shell 转成 **128+signum**
  （SIGSEGV→139、SIGABRT→134）**正常退出**，`WIFEXITED` 恒为真 —— 因此判据把
  `126/127/>=128` 一并视为"没跑起来"，不能只看 `WIFEXITED`。
- **P3**：**循环读干管道**才 `pclose`；单次 `fread` 后在输出超过缓冲时立刻关闭，
  会让子进程收到 SIGPIPE（假通过）或阻塞死锁。
- **不写 `/tmp`**：OHOS 上 `/tmp` 只读，中间文件落盘会让判据凭空失败。
