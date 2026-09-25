# libbs2b-tools 3.1.0 适配笔记

## 编译环境
- 构建系统: autotools (autoreconf -fi + configure + make)
- 编译日期: 2026-09-16
- 编译器: clang 15.0.4 / clang++ 15.0.4
- 依赖: libsndfile/1.2.2 (静态), 静态 libbs2b.a (本包内构建)

## 本包与库包的分工

| 归档 | 交付物 |
|------|--------|
| archives/l/libbs2b/3.1.0 | libbs2b.a/.so、bs2b.h 等头文件、libbs2b.pc |
| archives/l/libbs2b-tools/3.1.0 | bin/bs2bstream、bin/bs2bconvert |

库包在没有 libsndfile 的情况下只能出 bs2bstream（上游把 sndfile 设为硬依赖，
库包把它改成可选而已）。本包把 libsndfile/1.2.2 拉成真实依赖，
补齐库包产不出的 bs2bconvert，并在 package() 里删掉 include/ lib/ share/，
保证同一个文件只有一个属主。

## 关键问题

| # | 问题 | 根因 | 处理 |
|---|------|------|------|
| 1 | configure 直接报 "Please install libsndfile" 终止 | configure.ac 用 PKG_CHECK_EXISTS([sndfile], [], [AC_MSG_ERROR(...)]) 当硬依赖 | 补丁 0003 改为 HAS_SNDFILE + AC_SUBST + AM_CONDITIONAL，失败只 WARN |
| 2 | bs2bconvert 链接找不到 -lsndfile | src/Makefile.am 硬编码 -lsndfile 在 bs2bconvert_LDFLAGS，绕过 pkg-config | 补丁 0004 改为 LDADD 里的 @SNDFILE_LIBS@ + bs2bconvert_CFLAGS=@SNDFILE_CFLAGS@ |
| 3 | 静态 libsndfile 链接期 undefined pow/sin | -lm 只在 .pc 的 Libs.private 里 | 0003 用 `pkg-config --libs --static sndfile`；另外 make 时显式传 LIBS=-lm（$(LIBS) 位于 automake 链接行末尾，静态库顺序正确） |
| 4 | PKG_CHECK_EXISTS 找不到 sndfile | conan 不会把 PkgConfigDeps 的输出目录放进 PKG_CONFIG_PATH | generate() 里 PkgConfigDeps(self).generate() + tc.configure_args 追加 PKG_CONFIG_PATH=<generators_folder> |
| 5 | autoreconf 失败 / configure 无法重新生成 | 2009 年的 configure.ac 用了废弃的 AC_PROG_LIBTOOL 和 dist-lzma | 补丁 0003 换成 LT_INIT、去掉 dist-lzma |
| 6 | config.guess / config.sub 不认识 HarmonyOS | 2009 版脚本无 ohos 分支 | 补丁 0001 / 0002（复用库包同一份补丁） |
| 7 | config.status 临时目录不可写 | autoconf 用 umask 077 && mktemp -d 建 ./confXXXXXX，HMDFS 忽略 chmod | build() 里把 configure 的两处改写为 umask 000 + mkdir -p $TMPDIR/conf$$ （strict=False，找不到就跳过） |
| 8 | L2 冒烟失败 | 两个工具只认 argv[i][1]，--version/--help 都落到 default 分支 return 1，-h 也是 return 1 | 补丁 0005：补 -V/--version 与 --help，退出码 0（bs2bconvert 的 -h/--help 检查放在位置参数解析之前，避免 argc>=3 分支先报用法） |

## 构建步骤

1. `get()` 下载 libbs2b-3.1.0.tar.gz（sha256 已固定）并应用 0001-0005 补丁
2. `autoreconf -fi`（source_folder）
3. 改写新生成的 configure 里两处临时目录逻辑
4. `./configure --disable-shared --enable-static PKG_CONFIG_PATH=<generators>`
5. `make -j2 LIBS=-lm`
6. `make install DESTDIR=<package_folder>`，删除 include/ lib/ share/
7. ELF 自签名（llvm-objcopy 去掉旧 .codesign + binary-sign-tool selfSign）
8. 断言 bin/bs2bstream 与 bin/bs2bconvert 都存在（否则说明 pkg-config 没找到 sndfile）

## 验证方式

- `ohc-run.py conan-verify libbs2b-tools 3.1.0`：G0-G4 / L2 / L4 / L5
- `test_package/test.sh`：--version/--help 退出码契约、用 Python 标准库 wave 模块
  现场生成 16bit/44.1kHz 立体声 WAV，跑 bs2bconvert 后比对样本是否被 crossfeed
  改写、给 bs2bstream 灌原始 PCM 比对长度与内容、最后用不存在的输入文件作反例

## 未决 / 注意

- 上游没有测试套件（make check 为空），test_package 是本包唯一的自动化验证
- 本包不安装 man 页（share/ 整目录删除，与库包归口一致）