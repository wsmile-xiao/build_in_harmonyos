# libarc

libarc 是出云雅尚（Masanao Izumo）用 C 编写的微型解压库及示例程序，可读取十余种流行压缩归档的数据。当前支持的格式：tar（*.tar）、tar+gzip（*.tar.gz / *.tgz，deflate）、zip（*.zip，implode/deflate）、lzh（*.lzh，lh0-lh7/lzs/lz5/lz4）、MIME multipart。

## 功能概述

- 统一归档读取接口：`expand_archive_names` / `url_arc_open` / `url_read`
- 内建 deflate 压缩/解压缩：`arc_compress` / `arc_decompress`
- 归档类型探测：`get_archive_type`（纯扩展名/前缀映射）
- 条目通配符选择：`arc_wildmat` / `arc_case_wildmat`
- URL 抽象层（file / dir / http / ftp / news / mem / inflate / base64 等）
- 纯 C 实现（2000 年前后代码风格），无外部依赖，仅依赖 libc（含 socket）

## OHOS 适配要点

- **构建系统**: 手写 Makefile（非 autotools，无 configure 脚本）
- **交叉编译**: 上游 Makefile 硬编码 `CC = gcc` / `AR = ar -cr` / `PREFIX = /usr/local`，在 OHOS 上不可用。conanfile.py 不打补丁、不修改上游源码，直接用 OHOS toolchain（`tools.build:compiler_executables`，R33）编译上游 OBJS 的全部 29 个真实 C 源文件（`-O2 -Wall -fPIC`，另对 clang 15 降级 implicit 声明类错误为警告），并用 `llvm-ar rcs` 归档为 `libarc.a`
- **产物**: 静态库 `lib/libarc.a` + 公共头文件 `include/libarc/{url.h,arc.h,mblock.h,memb.h}`（与上游 install 目标一致）+ `licenses/COPYING`
- **示例工具**: 上游 `all` 默认不构建 `arccat`（需显式 `make arccat`），本次仅交付静态库（`package_type = "library"`，无 `commands.json`）
- **可移植性**: tar 解析为 ARM-safe 写法（`tar_checksum` 同时校验 signed/unsigned 两种校验和，`octal_value` 全程 `(unsigned char)` 强转），无 char 符号性陷阱
- **许可证**: GPL-2.0-or-later
- **无系统同名库**: `libarc` 非系统库，静态交付，无同名库冲突风险（R26/G3 无需处理）
- **公开 C API**（从源码头文件确认）:
  - `get_archive_type(char *)`（`.tar`→`ARCHIVE_TAR`、`.tgz`/`.tar.gz`→`ARCHIVE_TGZ`、`.zip`→`ARCHIVE_ZIP`、`.lzh`/`.lha`→`ARCHIVE_LZH`、`mail:`→`ARCHIVE_MIME`）
  - `arc_compress(void *, long, int, long *)` / `arc_decompress(void *, long, long *)`（注意：输入缓冲仅在零输出时由库 `free`，成功路径调用者自行释放）
  - `arc_wildmat(char *, char *)` / `arc_case_wildmat(char *, char *)`（返回 `TRUE=1` / `FALSE=0`）
  - `url_arc_open(char *name)`（`"file#entry"` 形式，使用前需 `url_add_modules` 注册 file/dir 等模块，用后 `url_close` + `free_archive_files`）
  - `ARC_LIB_VERSION`（`"2.0.2"`）/ `arc_lib_version` 符号
- **测试**: test_package 为真实功能测试（链接静态库；版本校验、7 种类型映射、通配符语义、压缩往返字节比对、手工 ustar 包端到端读回），非 include-only 测试

## 参考资料

- 上游发布目录：http://www.onicos.com/staff/iz/release/
- FreeBSD port：archivers/libarc（`USE_RC_SUBR` 无，`PORTVERSION=2.0.2`）
