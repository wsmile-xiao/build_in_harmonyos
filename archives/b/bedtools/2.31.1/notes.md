# bedtools 2.31.1 适配笔记

## 编译环境
- 构建系统: makefile（顶层 Makefile + 内置 htslib 的 htslib.mk，无 configure）
- 编译日期: 2026-07-14
- 编译器: clang/clang++（Alpine clang 15.0.7 / hnp 工具链），libc++
- 状态: built（容器内 conan create + test_package 通过）

## 上游构建系统分析

bedtools2 用纯 Makefile 构建：
- 顶层 `Makefile`：`SHELL := /bin/bash -e`，默认 `CXX = g++`，默认链接
  `BT_LIBS = -lz -lm -lbz2 -llzma -lpthread`，构建统一二进制 `bin/bedtools`。
- 内置 `src/utils/htslib`：由 `htslib.mk` 驱动编译为静态 `libhts.a`；无 configure
  脚本，缺 `config.h` 时由 Makefile 规则生成默认 `config.h`（硬编码
  `HAVE_LIBBZ2`/`HAVE_LIBLZMA`/`HAVE_LZMA_H`）。
- 安装规则 `make install`：把 `bin/*` 复制到 `$(DESTDIR)$(prefix)/bin`。

## 编译步骤

```
tar xzf bedtools-2.31.1.tar.gz && cd bedtools2
# 应用两份 portability 补丁（关闭 bz2/lzma）
patch -p1 < patches/0001-Makefile-disable-bz2-lzma.patch
patch -p1 < patches/0002-src-utils-htslib-Makefile-disable-bz2-lzma.patch
make -j1 \
  SHELL=/data/service/hnp/bin/bash \
  CXX=/data/service/hnp/bin/clang++ CC=/data/service/hnp/bin/clang \
  CPPFLAGS="-I<conan zlib include>" \
  CXXFLAGS="-stdlib=libc++" \
  LDFLAGS="-stdlib=libc++ -L<conan zlib lib>" \
  bin/bedtools
```

配方中编译器路径取自 Conan conf（`tools.build:compiler_executables:c/cpp`），
zlib 的 include/lib 取自 `self.dependencies["zlib"].cpp_info`，`-stdlib=libc++`
由 `self.settings.compiler.libcxx == "libc++"` 推导，均不依赖 shell 环境变量（R33）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 内置 htslib 默认链接 `-lbz2 -llzma` 且默认 `config.h` 硬编码 `HAVE_LIBBZ2`/`HAVE_LIBLZMA`/`HAVE_LZMA_H`，编译报 `bzlib.h`/`lzma.h` 找不到 | OHOS 工具链不提供 libbz2/liblzma 头文件与链接名（仅有 `libbz2.so.1.0`、`liblzma.so.5`，无 `libbz2.so`/`liblzma.so` 链接名） | 补丁移除顶层 `BT_LIBS` 与 htslib `htslib_default_libs` 中的 `-lbz2 -llzma`，并删掉默认 `config.h` 中三个相关 `#define`。bedtools 核心功能（BED/VCF 区间运算）不依赖 bz2/lzma，仅 bzip2 压缩输入与 CRAM 格式受影响 |
| 2 | `make: /bin/bash: No such file or directory` | bedtools `Makefile` 硬编码 `SHELL := /bin/bash -e`，OHOS 无 `/bin/bash` | make 命令行传 `SHELL=/data/service/hnp/bin/bash` 覆盖 |
| 3 | `iostream` 找不到、链接报 `undefined symbol: std::__1::...` | hnp clang 是 Alpine 版，默认未加 libc++ 头/库路径；bedtools 链接行只含 `ALL_LDFLAGS` 不含 `ALL_CXXFLAGS` | 编译与链接都传 `-stdlib=libc++`（CXXFLAGS + LDFLAGS） |
| 4 | `g++: command not found`（`CXX=g++` 默认） | Makefile 默认 `CXX = g++`，shell 环境变量 `CXX` 不会覆盖 Makefile 赋值 | make 命令行传 `CXX=...clang++`（命令行赋值优先于 Makefile 内赋值） |
| 5 | `llvm-ar` 不存在 | hnp 提供 `/data/service/hnp/bin/ar`，无 `llvm-ar`；htslib 默认 `AR = ar` | 不覆盖 AR/RANLIB，保证 `/data/service/hnp/bin` 在 PATH，让裸 `ar`/`ranlib` 解析 |
| 6 | `make all` 触发 `makeBashScripts.py`（需构建期 python）生成旧版 CLI 包装脚本 | `all` 目标含 `$(BIN_DIR)/intersectBed`，其 recipe 调用 `$(PYTHON)` | 改为只构建 `bin/bedtools`（统一二进制，所有子命令经 `bedtools <subcommand>` 访问），避开构建期对 python 的依赖 |

## 源码修改（补丁）

- `patches/0001-Makefile-disable-bz2-lzma.patch`：顶层 Makefile，`BT_LIBS` 去掉 `-lbz2 -llzma`。
- `patches/0002-src-utils-htslib-Makefile-disable-bz2-lzma.patch`：htslib Makefile，`htslib_default_libs` 去掉 `-lbz2 -llzma`；默认 `config.h` 生成规则删除 `HAVE_LIBBZ2`/`HAVE_LIBLZMA`/`HAVE_LZMA_H` 三组 `#define`（含其 `__APPLE__` 守卫）。

补丁为 git 风格（`a/`/`b/` 前缀，`patch -p1` 应用），由 Conan `apply_conandata_patches` 自动应用。

## 依赖版本

- zlib/1.3.1（Conan 提供，已发布于 ohpcd 制品仓）

## 验证结果

```
$ bin/bedtools --version
bedtools v2.31.1
$ printf "chr1\t10\t20\nchr1\t30\t40\n" > a.bed
$ printf "chr1\t15\t25\nchr1\t35\t45\n" > b.bed
$ bedtools intersect -a a.bed -b b.bed
chr1    15      20
chr1    35      40
$ readelf -d bin/bedtools | grep NEEDED
 NEEDED  libc++.so.1 / libc++abi.so.1 / libunwind.so.1 / libc.so   # zlib 静态链入，无 libz
$ file bin/bedtools
bin/bedtools: ELF 64-bit LSB arm64, PIE (DYN), 动态链接 musl libc
```

test_package/test.sh：`--version` PASS、`intersect`（逐字节比对预期区间）PASS、`sort`（已排序文件保持不变）PASS。

## 注意事项

- 关闭 bz2/lzma 是功能性取舍：bedtools 用于 BED/VCF/GFF/gzip 区间运算的核心能力不受影响；仅 bzip2 压缩输入与 CRAM 格式不可用。CRAM 主要用于 SAM/BAM 测序比对存储，非 bedtools 核心场景。
- 仅打包统一二进制 `bedtools`；上游的 `intersectBed`/`mergeBed` 等旧版包装脚本为 bash 别名（`bedtools <sub>`），未生成。
