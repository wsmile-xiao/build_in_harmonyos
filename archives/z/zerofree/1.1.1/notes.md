# zerofree 1.1.1 适配笔记

## 概述

把 `zerofree` 适配为 HarmonyOS PC 的 Conan `application` 包。它是一个单文件 C
程序（`zerofree.c`，约 200 行）+ 一份纯 GNU Makefile，整个 tarball 只有
`COPYING`、`Makefile`、`zerofree.c` 三个文件。

## 安装内容

- `bin/zerofree`
- `licenses/COPYING`

## 适配过程中的三个点

### 1. 纯 Makefile：`CC=gcc` + 链接行只有 `$(CFLAGS)`

上游 Makefile 全文只有 6 行：

```make
CC=gcc

all: zerofree.c
	$(CC) $(CFLAGS) -o zerofree zerofree.c -lext2fs

clean:
	/bin/rm -f *.o *~ zerofree
```

- `CC=gcc` 是普通赋值，`make CC=clang` 可覆盖，但沙箱里也**没有** `gcc` 别名可用，
  必须显式传交叉编译器；配方按 R33 从 `tools.build:compiler_executables` 取，
  而不是读未定义的 shell 变量（release worker 上该变量为空）。
- 链接行只带 `$(CFLAGS)`，依赖包的 `-I`/`-L` 无处可放。补丁 `0001`：

  ```diff
  -CC=gcc
  +CC?=gcc
  -	$(CC) $(CFLAGS) -o zerofree zerofree.c -lext2fs
  +	$(CC) $(CPPFLAGS) $(CFLAGS) -o zerofree zerofree.c $(LDFLAGS) -lext2fs $(LDLIBS)
  ```

  顺序是刻意的：`-lext2fs` 在 `$(LDFLAGS)` 之后（`-L` 先生效）、在 `$(LDLIBS)`
  之前（被 libext2fs 引用的 `com_err`/`uuid` 符号能随后被解析）。这与
  `no-more-secrets` 的 0001 补丁同因 —— 纯 Makefile 上游普遍不给交叉编译留口子。

### 2. 依赖复用已发布的 e2fsprogs

`-lext2fs` 来自已归档的 `e2fsprogs/1.47.4`（其 `package_info` 声明了
`ext2fs` component）。因此本包 `requires("e2fsprogs/1.47.4")`，用
`dependencies["e2fsprogs"].package_folder` 拼 `-I<inc>`/`-L<lib>`，**不**把
e2fsprogs 再携带一份。

e2fsprogs 默认静态发布（`--enable-static --disable-shared`），静态链接
`libext2fs.a` 需要补 `-lcom_err -luuid` 才能闭合 —— 这两个库同样由 e2fsprogs
自身提供。

### 3. 不调用 `make install`

上游没有 install 目标，OHOS 构建沙箱也没有 GNU coreutils `install`。
`package()` 直接 `copy()` 产物到 `bin/`，许可证到 `licenses/`。

## 上游测试情况

上游 tarball 里只有三个文件，**没有任何测试目标或测试目录**：

```
$ tar tzf zerofree-1.1.1.tgz
zerofree-1.1.1/COPYING
zerofree-1.1.1/Makefile
zerofree-1.1.1/zerofree.c
```

`make` 的目标只有 `all` 与 `clean`。因此**上游自动化用例数 = 0**。

所有验证在 `test_package/test.sh` 中完成（14 条断言）。

## 为什么测试用一个真实的 ext2 镜像

`zerofree` 的行为是"把空闲块重写为指定填充值"，只看它"退出码为 0"完全证明不了
它干了活。因此夹具是一个**真实的 1 MiB ext2 文件系统**：

```
Block count: 1024        (1 KiB blocks)
Free blocks: 970         (blocks 54-1023)
```

并在空闲区（block 512 起 100 个块，全部落在空闲范围内）写入了非零脏数据。
这样 `zerofree -nv` 的汇总里 `modified` 必然非零；真实运行后必须归零。
夹具以 gzip+base64 内嵌在 `test_package/data/`（2804 字节）。

`-v` 是拿到机器可读输出的开关：不加 `-v` 时 `zerofree -n` 什么都不打印
（进度条走 stderr，汇总走 stdout 且仅 `verbose` 时输出）：

```c
if ( verbose ) { printf(FORMAT, modified, free, ext2fs_blocks_count(fs->super)); }
```

## 验证结果

- 编译状态：通过
- 上游测试用例通过率：不适用（上游 0 个用例）
- 新增测试用例通过率：14/14（100%，脚本自报，与日志 `[ok]` 行数恒等）
- 门禁：`ohc-run.py conan-verify zerofree 1.1.1`

## 来源

- Source URL: `https://frippery.org/uml/zerofree-1.1.1.tgz`
- sha256: `956bc861b55ba0a2b7593c58d32339dab1a0e7da6ea2b813d27c80f8b723867`
- 上游项目: <https://frippery.org/uml/>
- 许可证: GPL-2.0-or-later
