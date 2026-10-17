# libarc 2.0.2 适配笔记

## 编译环境

- 构建系统: makefile（上游手写 Makefile，非 autotools，无 configure 脚本）
- 适配日期: 2026-09-16
- 编译器: clang 15（OHOS toolchain，`tools.build:compiler_executables`）
- 归档工具: llvm-ar
- 平台: OpenHarmony aarch64 (musl libc)
- 状态: built（配方已完成，待 HMBS 真机预检：conan create + test_package + 上游测试标记）

## 源码调查（三方交叉验证，未猜测）

| 项 | 值 | 来源 |
|----|----|------|
| 官方主页 | http://www.onicos.com/staff/iz/release/ | FreeBSD archivers/libarc port WWW 字段 |
| 首选下载 URL | http://distcache.freebsd.org/ports-distfiles/libarc-2.0.2.tar.gz（明文 http，规避 2026-09-15 真机实测的 https 证书 hostname mismatch） | FreeBSD 官方 distfile 镜像，实测可下载 |
| 回退下载 URL | https://www.onicos.com/staff/iz/release/libarc-2.0.2.tar.gz | 上游作者发布目录（2026-09 实测返回 403/404，保留为回退） |
| sha256 | a6778267610803c9607f26c5f77278840acff459bf518421a7b9be998b6fadf7 | 实测下载计算 + FreeBSD ports distinfo 一致 |
| 大小 | 97129 字节 | 实测（与 distinfo SIZE 一致） |
| 许可证 | GPL-2.0-or-later（GPLv2 或任何更新版本） | 上游 COPYING 文件头 + config.h 声明 |
| 目录结构 | 29 个 .c + 10 个 .h（含 libarc/ 下 4 个公开头）+ Makefile + config.h + COPYING，共约 46 文件 | 解压实测（tar 列表） |

### 公开 C API（从 libarc/arc.h、libarc/url.h 真实头文件确认）

```c
/* arc.h */
#define ARC_LIB_VERSION "2.0.2"
extern int get_archive_type(char *archive_name);
extern void *arc_compress(void *buff, long bufsiz, int compress_level, long *compressed_size);
extern void *arc_decompress(void *buff, long bufsiz, long *decompressed_size);
extern int arc_case_wildmat(char *text, char *p);
extern int arc_wildmat(char *text, char *p);
extern URL url_arc_open(char *name);   /* "filename#entry" */
extern void free_archive_files(void);

/* url.h */
extern URL url_open(char *url_string);
extern void url_close(URL url);
extern long url_read(URL url, void *buff, long n);
extern void url_add_modules(struct URL_module *m, ...);
```

> 注意：`arc_compress` / `arc_decompress` 仅在零输出时 `free(buff)` 并返回 NULL；成功路径输入缓冲仍归调用者释放（test_arc.c 据此编写，避免 double-free）。

## 上游测试核验（严格审计，未猜测）

### 1. 正式自动化测试：不存在（解包全树审计实证）

| 搜索项 | 结果 |
|--------|------|
| `test/` `tests/` `t/` 目录 | 不存在 |
| `make check` / `make test` 目标 | Makefile 目标仅有 all / arccat / clean / install |
| `TEST`/`TEST_F`（gtest） | 不存在 |
| CMakeLists.txt / CTestTestfile.cmake | 不存在 |
| configure / Makefile.am / configure.ac / meson.build | 不存在 |
| 文件名含 test 的源文件 | 不存在 |

**结论：上游正式自动化测试 = 0。**`url_news.c` 等 7 个文件内的 `#ifdef TEST` main() 为手写交互式演示程序（用法打印 + exit），无断言、无框架接线，不构成自动化套件，conanfile 不调用。

### 2. 同类佐证

FreeBSD archivers/libarc port（PORTVERSION=2.0.2）仅执行构建与安装（`arccat` + `libarc.so.1` + 6 头文件），无 `do-test` / `TEST_TARGET`。

## 编译方式

上游 `Makefile` 硬编码 `CC = gcc`、`AR = ar -cr`、`RANLIB = ranlib`、`PREFIX = /usr/local`，且 `all` 默认只构建静态库 `libarc.a`（`arccat` 需显式 `make arccat`，`readdir_win.o` 为 Windows 专用）。

**本次不打补丁、不修改任何上游源码**。conanfile.py 的 `build()` 直接：

1. 从 `tools.build:compiler_executables` 读取 OHOS clang/ar（R33：不从 shell env 取；ar 回退 `llvm-ar`）；
2. 用该 clang 编译上游 OBJS 的全部 29 个真实源文件（`-O2 -I. -Wall -fPIC`，另对 clang 15 把 `implicit-function-declaration` / `implicit-int` / `int-conversion` 降级为警告，cyrus-sasl 同类先例）；
3. 用 `llvm-ar rcs` 归档为 `libarc.a`。

`package()` 拷贝 `lib/libarc.a`、上游 install 目标一致的 4 个公共头（`libarc/{url,arc,mblock,memb}.h`）与 `licenses/COPYING`。仅交付静态库（`package_type = "library"`，无 `commands.json`，libb64 1.2.1 同类先例：其上游 `base64/` 命令行工具同样未交付）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游 Makefile 不适合 OHOS | 硬编码 gcc/ar/ranlib | 不打补丁，conanfile.py 直接调用 OHOS toolchain 编译 29 个真实 C 源文件 |
| 2 | 上游作者发布目录不可达（403/404）+ distcache https 在真机 TLS 校验失败（hostname mismatch） | 站点调整；FreeBSD 缓存 https 证书与主机名不匹配（2026-09-15 预检实测） | conandata.yml 以 FreeBSD 官方 distfile 镜像为首选（同包同哈希已验证），其中明文 http 版排第一以规避 TLS 校验失败，https 版第二，官方 URL 保留为最后回退；sha256 不变 |
| 3 | 上游无 check/test 目标 | 2000 年前后单作者库，无测试套件 | test_package 编写真实功能测试（5 组 CHECK-OK）；MANIFEST 上游审计按 `upstream_tests_exist: false` + 非空 `upstream_test_audit` 申报，conanfile 每次运行输出 `status:"no_tests"` 标记 |
| 4 | conanfile.py 不应裸用 ${CC}/${AR} | R33 铁律 | 用 `self.conf.get("tools.build:compiler_executables", check_type=dict)` 取编译器，ar 同理（env AR 仅为回退） |
| 5 | 压缩/解压接口存在条件性 free 入参语义 | arc.c：仅零输出时 `free(buff)` | test_arc.c 成功路径自行释放双缓冲，NULL 路径不再释放（注释写明），避免 double-free |
| 6 | 真机 `build()` 报 `/bin/sh: /data/service/hnp/bin/clang: inaccessible or not found`（exit 127） | conf 里的 hnp/bin 路径是 symlink 进 SDK 的链接，预检沙箱中目标不可挂载/不可执行；配方此前不校验直接 exec | 主配方与 test_package 均改为 verify-first 解析（R33 不变，conf 仍优先）：conf 路径仅在 isfile+X_OK 时采用，否则按 env CC/AR → PATH（shutil.which）→ 版本无关 SDK glob（`ohos-sdk.org/*/ohos/native/llvm/bin`，bubblewrap/crunch-dxtc 先例）→ hnp 显式路径逐个校验；全无可用时抛带 conf 值与 PATH 的明确错误（无则不再让 sh 报 inaccessible） |

## 源码修改

**无**。本次适配未修改任何上游源码，也未应用任何补丁（`patches_applied: []`）。

## 依赖版本

无外部依赖。libarc 是纯 C 库，编译和运行仅依赖：

- musl libc（系统自带，含 socket）
- clang 15（OHOS toolchain）
- llvm-ar（归档静态库）

## 测试说明

test_package/test_arc.c 是**真实功能测试**（非 include-only），共 5 组 `CHECK-OK` 断言：

1. 版本校验：`ARC_LIB_VERSION` 宏与 `arc_lib_version` 符号均为 `"2.0.2"`；
2. 类型映射：`get_archive_type` 对 `.tar` / `.tar.gz` / `.tgz` / `.zip` / `.lzh` / `.lha` / `mail:` 返回 `ARCHIVE_TAR/TGZ/ZIP/LZH/MIME`；
3. 通配符语义：`arc_wildmat` 大小写敏感匹配/不匹配 + `arc_case_wildmat` 大小写不敏感匹配/不匹配；
4. 压缩往返：`arc_compress` → `arc_decompress` 后长度与字节完全一致；
5. 端到端：手工构造最小 ustar 包（含 1 个 13 字节条目），经 `url_arc_open("test.tar#hi.txt")`（与 `arccat` 同路径，需先注册 file/dir URL 模块）读回并比对内容，读后 `url_close` + `free_archive_files` + 删除 fixture。

测试 fixture（`test_libarc.tar`）写在 `TMPDIR`（HMBS 注入的任务私有可写目录，缺省回退到 build 目录），不碰 `/tmp`。

## 真机验证（待 HMBS 预检回填）

- [ ] `conan create` 在 HarmonyOS aarch64 真机通过
- [ ] test_package 5/5 CHECK-OK，`HMBS_TEST_PACKAGE_RESULT` 标记正常
- [ ] `HMBS_UPSTREAM_TEST_RESULT` 输出 `status:"no_tests"`（上游审计见 test_package/MANIFEST.yml）
