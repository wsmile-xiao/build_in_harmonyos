# rsem 1.3.3 适配笔记

## 编译环境
- 构建系统: makefile（顶层 Makefile + 捆绑 samtools-1.3 的 configure/make）
- 编译日期: 2026-10-03
- 编译器: clang/clang++ 15.0.4（aarch64-unknown-linux-ohos，鸿蒙PC 真机原生）
- 状态: published

## 源码结构

rsem 上游将 samtools-1.3（含 htslib-1.3）和裁剪过的 header-only boost 1.55
打包进源码树，因此唯一外部编译依赖是 zlib。产物为 15 个 C++ 可执行程序 +
1 个捆绑 samtools + 15 个 perl 脚本。

## 编译步骤

```bash
# 1. samtools 子构建：config.status 在鸿蒙 HMDFS 上失败（见问题1），
#    用 Makefile 自带 sed 规则重建 config.mk，再手工追加覆盖项 + 生成 config.h
make -C samtools-1.3 config.mk
cat >> samtools-1.3/config.mk <<EOF
CC = clang
CFLAGS = -O2 -Wall
CURSES_LIB =
LIBS = -lz -lpthread
EOF
# config.h: 由 config.h.in 生成（#undef 全部注释掉，HAVE_LIBZ=1）
make -C samtools-1.3 -f Makefile samtools -j1 CC=clang AR=llvm-ar RANLIB=llvm-ranlib

# 2. rsem 本体（保持 gnu++98，见问题2）
make -j1 CXX=clang++ CXXFLAGS="-std=gnu++98 -Wall -O2 -I. -Isamtools-1.3/htslib-1.3 -I<zlib-include>" \
     LDFLAGS="-L<zlib-lib>"

# 3. 安装：真机无 install 工具，conan package() 显式拷贝（见问题4）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | samtools configure 的 config.status 报 `./confXXXX/subs1.awk: Permission denied`，config.h 无法生成 | HMDFS 对 conftest 临时目录的权限语义（E046 同类）；config.status awk 步骤无法执行 | 不走 configure：`make config.mk`（Makefile 内置 sed 规则）重建 config.mk 后追加 CC/CFLAGS/CURSES_LIB/LIBS；config.h 由 config.h.in 生成（#undef 注释化 + HAVE_LIBZ=1 + PACKAGE_VERSION） |
| 2 | boost 1.55 `boost/math/tools/tuple.hpp` 报 `no template named 'tuple' in namespace 'boost::math'` | libc++-ohos 在 gnu++98 模式下 `<tuple>` 头是空的；BOOST_NO_CXX11_HDR_TUPLE 检测失灵，第一个分支被误选 | 补丁 0001 强制 tuple.hpp 走 boost::fusion::tuple 分支（`#if 0` 掉 std/tr1 两分支） |
| 3 | 不能用 -std=gnu++11 编译：`SingleHit.h:46` 等报 `no viable conversion from 'std::istream' to 'bool'` | rsem 源码依赖 C++98 的隐式 istream->bool 转换（C++11 起 operator bool 为 explicit） | 保持 `-std=gnu++98`，问题2 的修复在 boost 侧做 |
| 4 | `make install` 报 `make: install: No such file or directory` | 鸿蒙真机无 coreutils `install` 工具 | conan package() 显式拷贝 bin 产物；不调用 make install |
| 5 | htslib 子 make 报 `gcc: No such file or directory` | `make samtools` 递归进入 htslib-1.3 时不继承命令行变量 | 在 make 命令行显式传 CC/AR/RANLIB（命令行变量对子 make 生效） |

## 源码修改

- `patches/0001-boost-math-tuple-force-fusion-fallback.patch`：
  boost/math/tools/tuple.hpp 将 std tuple / tr1 tuple 两分支 `#if 0`，
  强制使用 boost::fusion::tuple 兜底分支。无平台宏（PF5 合规）。

## 依赖版本

- zlib/1.3.1（conan 制品仓 ohpcd，链接 htslib/bam 的 -lz）

## 验证结果

```bash
rsem-simulate-reads  -> Usage banner, rc=0
rsem-samtools --version -> samtools 1.3 / htslib 1.3
rsem-samtools view -bS t.sam -o t.bam -> BAM 生成可回读
rsem-sam-validator t.sam -> rc=0
rsem-build-read-index 0 1 1 reads.fq -> reads.fq.ridx 生成
rsem-bam2readdepth t.bam out.depth -> chr1 逐碱基深度输出
16 个二进制全部可执行（R7 安全弹窗已逐一触发）
```

## 上游测试情况（R51）

上游 RSEM **无测试套件**（清点证据）：
- 源码树无 tests/ 目录（samtools-1.3/test/ 属捆绑 samtools 子项目）
- 顶层 Makefile 无 test/check 目标（`make check` 报 No rule to make target）
本适配在 test_package/ 补齐功能测试（test_rsem.py，8 项断言），
覆盖 SAM→BAM、校验、read index、读深统计与 usage 冒烟。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/rsem-* (15 个二进制) | rsem 核心 C++ 程序 |
| bin/rsem-samtools | 捆绑 samtools 1.3（重命名避免与系统 samtools 冲突，同 make install 规则） |
| bin/rsem-*.pl 脚本等 (15 个) | perl 前端脚本 + rsem_perl_utils.pm |

## 注意事项

- 运行 perl 前端（rsem-prepare-reference / rsem-calculate-expression）需要
  perl 解释器与 bowtie/bowtie2 比对器，属运行时外部依赖，不在本包构建范围。
- rsem-simulate-reads 等多线程程序链接 -lpthread 与 -lz，由 conan zlib 提供。
---

**编译结束**: 2026-10-03 08:55
**最终状态**: published
