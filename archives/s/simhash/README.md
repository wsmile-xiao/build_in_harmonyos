# simhash

> 文件相似度哈希工具：为文件生成 simhash，快速找出近似重复内容。

## 简介

simhash（Bart Massey）把文件内容压缩成"相似度哈希"：内容相近的文件其哈希位大量重合，
因此可以先为大量文件生成哈希、再只比较哈希来发现近似重复，无需反复读取原文。

用法（man 摘要）：

```
simhash [-s nshingles] [-f nfeatures] file            # 生成哈希（输出到文件）
simhash [-s nshingles] [-f nfeatures] -w file ...     # 与多个哈希比较
simhash [-s nshingles] [-f nfeatures] -m file ...     # 多路模式
simhash -c hashfile hashfile                          # 比较两个哈希，打印相似度
```

## OHOS 适配要点

- 上游是裸 `Makefile`，硬编码 `CC=gcc` 与 `-O4 -ansi -pedantic`（OHOS 无 gcc、clang 无 `-O4`），
  且 `install` 写到 `/usr/local`。本仓库在配方内直接用 Conan 提供的 clang 编译四个 `.c`
  并自行安装：
  `clang -O3 -Wall -o simhash simhash.c crc32.c heap.c hash.c -lm`。
- 命令行工具 → 提供软件级 `commands.json`（R38/L0k）。
- 上游 `test.sh` 是手工相似度矩阵（需人工准备 `a`/`b` 文件、无断言），故 R51 上游步骤申报
  `not_applicable`；功能验证由 `test_package` 的 Python harness 完成。
- 产物：`bin/simhash`、`share/man/man1/simhash.1`、`licenses/COPYING`。

## 依赖

无（仅链接 `-lm`）。

## 使用

```sh
simhash -f 64 -s 4 a.txt > a.sim   # 生成哈希
simhash -f 64 -s 4 b.txt > b.sim
simhash -c a.sim b.sim             # 打印相似度：相同 1.0 / 近似 0.8x / 无关 .00
```

## 功能验证

```sh
conan create archives/s/simhash/0.0.20161225 -pr:h=ohos-aarch64 -pr:b=ohos-aarch64 --build=missing
# rc=0；CLI harness 9/9（相同=1.0、改一词>0.5、无关=.00、-c 恒退出 0、man 已安装）
```
