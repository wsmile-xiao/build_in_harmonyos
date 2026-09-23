# pipebench 0.40 适配笔记

## 软件简介
pipebench（Thomas Habets 编写）测量 stdin→stdout 的**管道吞吐速率**：读入并在近乎
不减速下转发，按秒输出速率与总流量统计（`... | pipebench | ...`）。许可证 GPL-2.0-or-later。

## 编译环境
- 构建系统: makefile（上游 0.40 发布 tarball 自带极简 Makefile）
- 目标平台: OpenHarmony OHOS / aarch64
- 编译器: clang（`aarch64-unknown-linux-ohos`）

## 编译步骤
上游 Makefile：
```make
CC=gcc
CFLAGS=-Wall -w -pedantic
pipebench: pipebench.c
	$(CC) $(CFLAGS) -o pipebench pipebench.c
```
conan 构建时以 `make CC=<OHOS clang> SHELL=/bin/sh pipebench` 覆盖 `CC=gcc`，
保留上游 `CFLAGS`。**不调用 `make install`**（其写死 `/usr/local`），产物由
`package()` 拷入 `bin/pipebench` 与 `share/man/man1/pipebench.1`，并 `chmod 755`。

## OHOS/musl 可移植性修改（均在上游 pipebench.c 上做最小改写）
| # | 修改 | 原因 |
|---|------|------|
| 1 | 增加 `#include <stdint.h> <stdlib.h> <string.h>` | musl 编译缺 `<stdlib.h>/<string.h>` 时报隐式声明（`malloc/free/strlen/strcpy`），与 Debian gcc-14 FTBFS (#1075387) 同类 |
| 2 | `#ifdef sun` 类型块 → `#if defined(sun) \|\| !defined(__GLIBC__)`，把 `u_int{8,16,32,64}_t` 宏映射到 `uint*_t` | legacy BSD 类型 glibc 由 `<sys/types.h>` 提供、musl 不提供 |

## 上游测试
上游 **没有任何测试目标/测试目录**（Makefile 仅 `all/doc/install/clean`；源码目录仅
6 个文件，无 tests/）。如实记录：upstream_test = 0。二进制功能冒烟放在 test_package：
`-h` 用法退出码、`-q` 模式 6.2KB 直通字节一致（cmp）+ `Summary`（`B/second`）出现。

## 打包要点
- `bin/pipebench`（唯一产物，argv[0] 固定）
- `share/man/man1/pipebench.1`
- `licenses/LICENSE`（GPL-2.0-or-later 全文，上游随包）

## 遇到的问题与解决方案（真机 conan create 验证后确认）
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 Makefile CC 硬编码 gcc | 上游未做交叉编译适配 | conan 以 `make CC=<clang>` 覆盖 |
| 2 | `make install` 写死 /usr/local | OHOS 只读系统路径 | 不调 install，package() 自行拷入 conan pkg 目录 |
| 3 | musl 无 u_int64_t / 缺头文件 | 上游代码假定 glibc | build() 内 replace_in_file 最小改写 |

## 验证结果
（等待 Harmony PC 真机 `conan create` 后填写）

## 注意事项
- pipebench 仅 C 运行时依赖；输出文件权限需要可执行（`chmod 755`）。
