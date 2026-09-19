# libxar 1.8.0.498 适配笔记

## 编译环境
- 构建系统: autotools（configure 预生成，autoconf 2.59 时代）
- 编译日期: 2026-09-19
- 编译器: clang（OHOS aarch64 原生构建）
- 状态: built

## 上游与版本
- 上游: Apple 官方开源发行 apple-oss-distributions/xar，tag `xar-498`（R39 合规）。
  Debian/Ubuntu 的 xar 1.8.0.498 即此源码（dversionmangle `s/^1\.8\.0\.//`，
  见 debian/watch）；xar-498 内 configure.ac 版本串为 `1.8dev`，`1.8.0.498`
  为发行版对 Apple build 号 498 的规范命名，本任务沿用平台指定版本号。
- 净新适配：本仓库 archives 此前无 xar/libxar（W0 版本占用 missing）。
- 平台另有独立任务 xar 1.8.0.498（id 12036）针对 CLI 工具，本包按上游默认
  同时产出库与 CLI（xar 的 Makefile 不可拆分构建库/工具）。

## 编译步骤

conan create（finish 内部同链路）：
1. source(): 下载 tarball（sha256 校验），将 autoconf 子目录 xar/ 上移为源码根
2. generate(): 生成 mktemp 包装（E011）与 xml2-config 包装（见下），注入
   CPPFLAGS/LDFLAGS/LIBS（依赖 conan 缓存路径 + -lcrypto/-lbz2）
3. build(): apply_conandata_patches（8 个补丁）→ umask 077→022 →
   configure（--disable-shared --enable-static，见问题 15）→ make
   （原生 aarch64，config.guess 识别 HarmonyOS 产出 aarch64-unknown-linux-ohos）
4. package(): make install（include/xar/xar.h、lib/libxar.a、bin/xar、man1），
   移除 libxar.la

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 2005 年版不识别 HarmonyOS（E007） | uname -s = HarmonyOS 无匹配分支 | 官方 patch-autotools-ohos.pl 可用（config.guess 部分生效） |
| 2 | config.sub 2005 年版脚本补丁 0 处生效；且不认识 aarch64 | 脚本匹配模式针对新版文件；aarch64 为 2012+ CPU 名 | 手写补丁：CPU 列表补 aarch64/aarch64_be（裸+带厂商两种）、KERNEL-OS 分离列表补 linux-ohos*、OS 校验显式接受 -linux-ohos* 与 -ohos*（防 -linux*) 兜底把 os 改写成 linux-gnu-ohos）；本地 sh 实测 2/3 段三元组均归一化为 aarch64-unknown-linux-ohos |
| 3 | configure 阶段 xml2-config 缺失即 AC_MSG_ERROR；conan libxml2 自带的 xml2-config 硬编码 /usr/local（juise 同款问题） | configure 以 `AC_PATH_PROG(xml2-config)` + `--cflags/--libs` 取路径 | 配方生成包装脚本输出 conan 缓存真实路径，经 `--with-xml2-config=<wrapper>` 传入（xar 特有入口，无需改源码） |
| 4 | E011：configure 2 处 umask 077 + mktemp -d 在 HMDFS 产生不可写临时目录（同 xz） | hmdfs UID 映射 + 0700 权限 | mktemp 包装返回失败走 mkdir 兜底 + build() 中 umask 077→022（运行时替换，与 xz 5.8.3 相同） |
| 5 | hash.c（非 Apple 平台）无条件 `#include <openssl/evp.h>`，而 configure 完全不检测 OpenSSL，LIBS 亦不含 -lcrypto | Apple 版仅面向 CommonCrypto/OpenSSL 双轨，未写检测 | CPPFLAGS 注入 openssl include，LIBS 注入 -lcrypto（不改源码）；消费者测试 sha256/sha512 TOC 校验和覆盖该链路 |
| 6 | lzmaxar.c 全部代码在 #ifdef HAVE_LIBLZMA 内，但 configure 从不定义该宏（Apple 版默认无 lzma） | 上游仅保留代码未接 configure | 保持上游默认不启用 lzma（曾尝试注入 -DHAVE_LIBLZMA，因问题 #10 的旧 API 冲突放弃），消费者测试不含 lzma round-trip |
| 7 | configure 的 AC_CHECK_FUNC(asprintf) 在原生运行下正常；bionic 有 asprintf | -D_GNU_SOURCE 由 configure 的 *-*-linux* 分支注入 | 无需处理（aarch64-unknown-linux-ohos 命中 *-*-linux* 分支） |
| 8 | `include/xar.h:268:39: error: expected function body after function declarator`（xar_get_safe_path 声明） | 上游 bug：xar.h 非 Apple 分支只定义了 API_DEPRECATED 空宏，漏了 API_AVAILABLE——`API_AVAILABLE(macos(12.0))` 被当作函数体解析；archive.c 的隐式声明错误为连带 | 补丁 0002：在既有 #else 分支内补 `#define API_AVAILABLE(...)`（无新增平台宏，PF5 合规） |
| 9 | `make: jobserver mkfifo: ... Operation not permitted` | make jobserver fifo 在 HMDFS TMPDIR 上受限 | 非阻塞：make 自动降级串行，编译结果不受影响 |
| 10 | `lzmaxar.c:121/255-270: use of undeclared identifier 'LZMA_FILTER_COPY'/'lzma_preset_lzma'/'LZMA_STREAM_INIT_VAR'/'lzma_memlimit_alloc'` 等 11 个错误 | lib/lzmaxar.c 针对 2006 年 LZMA SDK 4.42 API 编写，这些符号 xz 5.x 已全部移除；上游 configure 也从不定义 HAVE_LIBLZMA（默认不启用） | **保持上游默认不启用 lzma**（不注入 -DHAVE_LIBLZMA），产物支持 none/gzip/bzip2 三种编码；不强行移植其他 fork 的 lzmaxar 改写 |
| 11 | `linuxattr.c:229: error: incompatible integer to pointer conversion`（`bname = safe_dirname(tmp)`） | 上游笔误：函数实际名为 util.h 的 `xar_safe_dirname`；该分支仅在 `HAVE_LSETXATTR && !__APPLE__` 时编译，Apple 构建不触及，glibc/gcc 时代仅警告、clang 15 起为 error | 补丁 0003：改调用 `xar_safe_dirname`（一行） |
| 12 | `hash.c:100: error: field has incomplete type 'EVP_MD_CTX'` | OpenSSL 1.1/3.x 起 EVP_MD_CTX 不透明（前向声明），xar-498 按 1.0.x 公有结构体按值内嵌，且 DigestInit/Update/Final 均取 `&` 地址 | 补丁 0004：字段改 `EVP_MD_CTX *`，new 分配 EVP_MD_CTX_new，Update/Final 直传指针，finish 时 EVP_MD_CTX_free |
| 13 | `util.c:592: error: variable has incomplete type 'struct statfs'` + `MNT_LOCAL` 未声明 | `xar_optimal_io_size_at_path` 使用 BSD/macOS 的 MNT_LOCAL 挂载标记；bionic 的 sys/mount.h 无 statfs 定义与该常量（glibc 亦无 MNT_LOCAL） | 补丁 0005：`#ifdef MNT_LOCAL` 包裹探测块，无标记平台返回 1MiB 默认 rsize（等价上游默认路径） |
| 14 | `src/xar.c:39: fatal error: 'fts.h' file not found`（库全部编译链接成功后） | bionic 无 fts(3)；xar CLI 的 `xar -c` 目录用 fts 遍历目录并做 exclude 正则匹配。glibc 有 libfts、musl 发行版靠 musl-fts 包（Alpine 对本包即此方案），bionic 无对应包 | 补丁 0006：vendor musl-fts 1.2.7（BSD-3， Regents of the University of California；源 https://github.com/void-linux/musl-fts ）到 src/（fts.h/fts.c，fts.c 自引用改 "fts.h"），XAR_SRCS 加 fts.c，xar.c include 改引号；仅编入 CLI，libxar 库不受影响 |
| 15 | 安装版 CLI（ixar→bin/xar）运行报 `Error loading shared library libxar.so.1` | 上游默认 shared=yes 时 ixar 链接共享库 libxar.so.1，RUNPATH 为 configure 期 LIBDIR（conan 2 配置期无法预知最终包目录，实测为 `//lib`）→ 运行期定位失败；且 OHOS 运行时 LD_LIBRARY_PATH 不可靠 | 配方加 `--disable-shared --enable-static`（上游自带选项）：ixar 静态链 libxar.a 自含运行，xz 5.8.3 工具 `-static` 同款思路；库交付口径变为静态 libxar.a |
| 16 | CLI 一切短选项（-c/-t/-x/-f）均打印 usage 退出，`--version` 却正常 | ARM/OHOS 上 char 默认 **unsigned**：`char c` 接 getopt_long 的 -1（EOF）变成 255，`c != -1` 恒真，循环把 EOF 当未知选项落入 default→usage。最小 getopt 探针（int c）同 optstring 实测正常，插桩打印 c=255 确证 | 补丁 0008：`char c` 改 `int c`（一行） |

## 源码修改

8 个补丁（均已在干净 git 仓库 `git apply --check` 验证）：

- `patches/0001-config-guess-sub-ohos.patch` — config.guess 加 `*:HarmonyOS:*:*`
  分支（官方脚本产物改写为 2005 echo/exit 风格）；config.sub 补 aarch64 与
  linux-ohos 识别（手写，三种三元组形态本地实测通过）
- `patches/0002-xar-h-api-available.patch` — xar.h 非 Apple 分支补
  API_AVAILABLE 空宏（上游 bug，随 xar_get_safe_path 引入）
- `patches/0003-linuxattr-safe-dirname.patch` — linuxattr.c 函数名笔误修复
  （上游 bug，仅非 Apple + HAVE_LSETXATTR 时编译）
- `patches/0004-hash-openssl3-opaque-ctx.patch` — OpenSSL 3 不透明 EVP_MD_CTX
  兼容（字段改指针 + new/free 管理）
- `patches/0005-util-optimal-io-mnt-local.patch` — MNT_LOCAL 探测块按常量
  存在性编译（bionic/glibc 走 1MiB 默认）
- `patches/0006-fts-bionic-vendored.patch` — vendor musl-fts 1.2.7（BSD-3）
  供 CLI 使用；fts.c 仅改自引用 include 为 "fts.h"，其余原样
- `patches/0007-src-include-path.patch` — CLI include 路径修正：
  xar_internal.h `<xar/xar.h>`→`"xar.h"`、xar.c lib 头改 `../lib/`
  （Debian Fix-include-path 同款，其内容取自 Fedora xar.spec）
- `patches/0008-xar-getopt-int-c.patch` — main 的 getopt 返回值 `char c`→
  `int c`（ARM unsigned char 使 -1 变 255，短选项全失效）

## 与 Debian 1.8.0.498-3 补丁对照（独立佐证）

| Debian 补丁 | 本任务对应 |
|------|------|
| Don-t-do-availability-stuff-on-non-Darwin | 0002（API_AVAILABLE/API_DEPRECATED 空宏） |
| linuxattr-fix-missing-symbol-safe_dirname | 0003（同名同因，独立确证） |
| Fix-compatibility-with-openssl-1.0 | 0004（方向相反：其兼容旧 1.0，我方兼容新 3.x 不透明 EVP_MD_CTX） |
| Fix-include-path | 0007（同款） |
| Fix-arm-and-ppc64 / Fix-configure.ac / Update-configure.ac-for-newer-build-system / No-rpath | 本任务未涉及（0001 覆盖 arm64 识别；rpath 由 conan 管理） |
| （Debian 无对应） | 0001 config.guess/sub OHOS、0005 MNT_LOCAL、0006 vendored fts |

build() 运行时替换（不入补丁，与 xz 5.8.3 相同口径）：configure 的
umask 077→022（E011）；tarball 内 config.status 为上游误提交的构建残留，
configure 重新生成覆盖，不使用。

## 依赖版本

| 依赖 | 版本 | 用途 |
|------|------|------|
| zlib | 1.3.2 | gzip 编码 + TOC/堆压缩底层 |
| bzip2 | 1.0.8 | bzip2 编码（HAVE_LIBBZ2，configure 自查） |
| libxml2 | 2.15.3.1 | TOC XML 解析/生成（xml2-config 包装） |
| openssl | 3.5.8.1 | libcrypto 摘要（sha1/sha256/sha512，EVP 注入链接） |

注：W0 曾核验 xz/5.8.3.2 可用，后按上游默认不启用 lzma（问题 #10），
requires 不含 xz。

## 验证结果

```bash
# conan create（2026-09-19 设备实测，私有 CONAN_HOME，试构建 15 轮收敛后全绿）
conan create archives/l/libxar/1.8.0.498 \
  -pr:h ci/conan/profiles/ohos-aarch64 -pr:b ci/conan/profiles/ohos-aarch64
# test_package：test_xar_probe 3/3 PASS（none/gzip/bzip2 × sha1/sha256/sha512 round-trip）
# CLI 冒烟：xar -c 建档 + xar -t 列档 PASS
```

上游测试实跑（R51 三步法）：57 用例 → **PASS 32 / SKIP 14 / FAIL 11**。
逐项原因（lzma/xattr 跳过、mtime 整秒、hmdfs 硬链接）与原件日志哈希见
`reports/upstream-tests-log.md`。

制品基线（reports/baseline.json）：每轮验证使用随机命名的私有 CONAN_HOME，
ELF 制品内嵌的构建路径/RUNPATH 逐轮变化（bin/xar、lib/libxar.a），同源码重验
时 L5 与旧基线必有差异。按验证器指引删除 baseline.json 重立基线（语义等同
首轮），制品差异源于构建路径而非源码/配方变更。

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| include/xar/xar.h | 11728 | 公共头 |
| lib/libxar.a | 188464 | 静态库 |
| bin/xar | 4282880 | CLI（静态自含，动态依赖 libxml2.so 经 RUNPATH 解析） |
| share/man/man1/xar.1 | 5874 | 手册 |

## 注意事项

- 本包编码能力为 none/gzip/bzip2（上游 498 默认口径）；xz 压缩的 xar 档案
  无法读取（上游 lzmaxar 依赖旧 LZMA SDK，问题 #10），已如实申报。
- 库交付口径为静态 libxar.a（问题 #15）；消费者 cpp_info.requires 已带全部
  传递依赖（zlib/bzip2/libxml2/openssl）。
- 上游 test/ 为 Python 2 时代脚本（cStringIO、`except X, e`、func_name），
  且 util.py 顶层依赖 xattr 模块（设备无、且非库消费者必需）——R51 实测
  采用最小可披露修改的 python3 副本，逐项结果见 reports/upstream-tests-log.md。
- 包含 CLI 工具 bin/xar，已按 R38 在软件级声明 commands.json。
