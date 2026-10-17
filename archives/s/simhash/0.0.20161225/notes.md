# simhash 0.0.20161225 适配笔记

## 编译环境
- 构建系统: 上游为裸 `Makefile`（无 configure）
- 编译日期: 2026-09-18
- 编译器: OHOS clang（Conan profile `ohos-aarch64`）
- 状态: built

## 版本与源码
- 平台版本 `0.0.20161225` == Debian `simhash_0.0.20161225.orig.tar.gz`
- sha256 `5f0dec01e7e3de713e809e4524f90547505dc8ac20d003782e83564f6395a12e`

## 产物
- `bin/simhash`
- `share/man/man1/simhash.1`（源文件名为 `simhash.man`，安装时改名为 `.1`）
- `licenses/COPYING`
- 软件级 `commands.json`（CLI 工具，R38/L0k）

## 源码修改

无补丁。上游 Makefile 不适用的两点在配方内处理：

| 上游写法 | 问题 | 本仓库做法 |
|----------|------|-----------|
| `CC=gcc`、`CFLAGS=-g -O4 -Wall -ansi -pedantic` | OHOS 无 gcc；clang 无 `-O4`；`-ansi` 对本工程无必要 | `build()` 直接用 Conan 提供的 clang：`clang -O3 -Wall -o simhash simhash.c crc32.c heap.c hash.c -lm` |
| `install: cp simhash $(BIN)`（`DESTDIR=/usr/local`） | 会写到 `/usr/local` | `package()` 自行安装 `bin/`、`share/man/man1/`、`licenses/` |

## 上游行为要点（消费者测试依据）

- `simhash -f <nfeatures> -s <nshingles> <file>` 生成哈希文件（二进制，`-f`/`-s` 决定大小与内容）。
- `simhash -c <hashfile> <hashfile>` 打印**相似度**并**始终退出 0**：相同文件 `1.0`、
  改一个词 `.81`、完全无关 `.00`（实测）。
- 上游 `test.sh` 是手工相似度矩阵：需要人工准备 `a`/`b` 文件，且只打印矩阵、无断言
  → R51 上游步骤申报 `not_applicable`。

## 消费者测试（9 项检查）

`test_package/test_simhash.py` 通过真机运行安装后的 CLI：

1. 已安装 `bin/simhash` 存在
2. `-f 64 -s 4` 生成非空哈希文件且退出 0
3. 三个文件的哈希文件大小一致
4. 相同文件比较 == `1.0`
5. 改一个词的比较 > `0.5`（实测 0.81）
6. 完全无关内容比较 == `0.0`
7. 比较（即使不相似）退出码为 0
8. 不同 `-f`/`-s` 参数产生不同哈希（字节不同）
9. `share/man/man1/simhash.1` 已安装

（共 9 项检查，其中第 3 项为大小一致性。）

## 验证结果

```sh
conan create archives/s/simhash/0.0.20161225 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# rc=0；CLI harness 全部通过
```
