# xar 1.8.0.498 — 适配工作笔记（Windows 阶段 1，2026-09-27）

任务：ohpcd 平台 xar 1.8.0.498（contrib-12036，已绑定当前账号）· 分支
`feat/xar-1.8.0.498`（以平台实际显示为准）。

## W0 依赖分析（configure.ac 实测）

| 依赖 | 性质 | 处理 |
|------|------|------|
| libxml2 | 硬依赖（xml2-config 探测 + AC_CHECK_HEADER xmlwriter，缺则 AC_MSG_ERROR） | require libxml2/2.15.3.1；cmake 包不含 xml2-config → 配方写 shim |
| zlib | 硬依赖（AC_CHECK_HEADERS zlib.h + AC_CHECK_LIB z） | require zlib/1.3.1 |
| bzip2 | 可选（命中定义 HAVE_LIBBZ2） | require bzip2/1.0.8.2，保留完整压缩支持 |
| openssl | **非 Apple 平台隐式硬依赖**：lib/hash.c #else 分支无条件 include <openssl/evp.h>，configure.ac 无任何检测（Apple 只走 CommonCrypto） | require openssl/3.5.8.1；头路径经 AutotoolsDeps，链接经 `LIBS="-lcrypto"` |
| pthread / acl | 可选，探测失败自动降级 | 不 require（musl 自带 pthread 符号） |
| lzma | configure 无探测（HAVE_LIBLZMA 恒不定义，代码 #ifdef 守卫） | 不启用 |

R35（MateBook）：conan download libxml2/2.15.3.1、zlib/1.3.1、
bzip2/1.0.8.2、openssl/3.5.8.1（仅 --only-recipe 不足以证明二进制可用，
须下载制品确认）。

## W0b 历史知识核验

- E007（config.guess 不识别 HarmonyOS/aarch64）→ 本任务不走补丁脚本
  路线，见下；gtypist/2.10.1 是补丁脚本路线先例。
- xml2-config shim 先例：aspectc/2.5（已合入）。
- §12.38① env -u CONFIG_SHELL + 绝对路径：gtypist；E114 umask
  077→022：zzuf/jailkit；E074 -j1：tarsnap 等。

## 源码要点（xar-498 tag tarball 实测）

- sha256 `9cee4f80b96cf592ccc545a4fdd51e4da4a5bd3b4734901637d67b043eff3c75`；
  版本口径：1.8.0.498 = apple-oss-distributions xar-498（1.8.0 系列
  修订 498）；源码内部版本串 1.8dev → `xar --version` 输出
  **"xar 1.8dev"**（消费者断言按此口径，notes/manifest 均已注明）。
  mackyle/xar 仓库仅发布 1.6.1 及更早，无 1.8.x 归档（tag/release 均
  实测核查）。
- 构建体系在 tarball 的 **xar/ 子目录**：手写根 Makefile.in include
  lib/src 的 Makefile.inc（非 automake），configure（autoconf 2.59）
  预生成 → in-source 构建、无需 bootstrap。
- **config.guess/sub 为 2005-07-08 版**：设备 uname -s=HarmonyOS、
  aarch64 均无法识别（E007）。本任务采用绕开路线：configure 对 host
  的全部用途是 `*-*-linux*` case 匹配（选 abi=elf、RPATH、
  -D_GNU_SOURCE）；类型探测（ino_t/dev_t 尺寸）均为 AC_CHECK_SIZEOF
  编译期行为，与 host 别名无关；configure.ac 无 AC_RUN_IFELSE。
  → 传 `--build=x86_64-linux --host=x86_64-linux`（2005 config.sub
  实测 canonicalize 为 x86_64-pc-linux-gnu），build==host → 原生模式，
  config.guess 不运行。CC 由 profile 提供（OHOS aarch64 clang）。
- **补丁（conandata 唯一补丁）**：hash.c 非 Apple 分支 `EVP_MD_CTX
  digest;` 栈上声明 —— EVP_MD_CTX 自 OpenSSL 1.1.0 起为不透明类型
  （3.5 头文件实测 typedef struct evp_md_ctx_st EVP_MD_CTX; 无公开
  struct 定义），无法编译 → 改 EVP_MD_CTX_new/free 句柄式（3 处调用
  + 1 处 struct 字段 + finish 追加 free）。补丁已本机
  `patch -p1 --dry-run` 验证可应用。其余 EVP API（DigestInit/Update/
  Final/get_digestbyname/OpenSSL_add_all_digests）在 3.x 仍存在（部分
  仅 deprecated 警告，无 -Werror）。
- macho.c 无条件编译但自包含（自带 struct mach_header 定义，不依赖
  mach/ 头）；linuxattr.c 需 sys/xattr.h（musl 有）。
- `make install` 安装 src/ixar 为 bin/xar：ixar 以 RPATH=<LIBDIR> 链
  共享 libxar → 配方用 **--disable-shared** 静态链，包内二进制自包含；
  include/xar.h + lib/libxar.a 仍随 install 打包。
- 顶层 tarball 的 xarsig/、xar.xcodeproj、patches/appleadditions.diff
  均为 Apple 构建专用，不参与 xar/ 子目录构建。

## 测试计划

- 构建自检（配方 build()，1 项）：真实归档管线 —— 2 文件（含 1KB
  二进制）`xar -czf` 创建 → 解出 → cmp 逐字节一致。
- 消费者（test_xar.sh，6 项）：--version / -cf 创建 / -tf 列表 /
  -xf 解出逐字节一致 / --compression=gzip roundtrip / --dump-toc
  XML TOC（含成员名与 sha1 校验和元素，默认 TOC 校验和上游定为
  SHA1，archive.c:277）。全部离线、确定性。

## 真机验证修正记录（2026-09-27，SHA ee67a946 第 2 轮中止后修正）

第 2 轮 configure 全过（EVP 补丁、xml2-config shim、--build/--host
三元组绕过均按预期工作），死在 make：`make -C <src>/xar` 找不到
Makefile。根因：conan create 下 source/build 是两个缓存目录，
self.run() 的 cwd 是构建根——`sh {src}/configure` 运行时 config.status
把 Makefile 写到了 cwd（构建根），不在源码树。修复：configure 命令
前置 `cd "{src}"` 真正 in-source 生成（make -C src / install / 自检
本就以 src 为基准，其余不变）。

### 第 4 轮（SHA 9f989543）中止后修正：API_AVAILABLE 非Apple 缺口

第 4 轮 configure 全过、cd 修复生效，死于 lib/archive.static.o 编译：
`include/xar.h:268: error: expected function body after function
declarator`（xar_get_safe_path 声明尾的 API_AVAILABLE(macos(12.0))）。
根因：xar.h 的 Apple/非 Apple 分支不对称——非 Apple 只空定义了
API_DEPRECATED，漏了 API_AVAILABLE；OHOS clang（非 Apple）下该宏
未定义。受影响声明共 4 处：xar.h:268（xar_get_safe_path）+
src/xar_internal.h:18/19/20（xar_open / xar_open_digest_verify /
xar_get_path，该文件 include "xar.h"，补 include 即全覆盖）；
API_DEPRECATED 非 Apple 分支已定义为空无需处理；实现（lib/util.c）
与调用方均无 Apple 分支，功能本体可用。修复：新增
patches/0002-api-available-nonapple.patch（xar.h.in 非 Apple 分支
补 `#define API_AVAILABLE(...)`，单一职责与 0001 分开），conandata
补丁条目与 sha256 同步。补丁已本机 `patch -p1 --dry-run` 按
0001→0002 顺序验证可应用。

### 第 5 轮（SHA 21224458）中止后修正：linuxattr.c 上游笔误

第 5 轮 0002 补丁生效（API_AVAILABLE 首错消除），编译推进到
linuxattr.c 后死在新首错：`lib/linuxattr.c:229: call to undeclared
function 'safe_dirname'`。根因是上游笔误：全源码树无 safe_dirname
符号（实际函数为 xar_safe_dirname，lib/util.h:56 声明、util.c:122
定义）；同文件其余调用点（archive.c/darwinattr.c/filetree.c 共 7
处）均带 xar_ 前缀，唯 linuxattr.c:229 漏。该代码路径由
HAVE_SYS_XATTR_H && HAVE_LSETXATTR && !__APPLE__ 守卫——OHOS musl
提供 sys/xattr.h 且 configure 探到 lsetxattr，守卫为真；Apple 上被
!__APPLE__ 掩盖，上游从未发现。修复：新增
patches/0003-linuxattr-safe-dirname.patch（单行
safe_dirname(tmp) → xar_safe_dirname(tmp)，返回 malloc'd 字符串、
调用点随后 free，语义匹配），conandata 条目 + sha256 同步；本机
patch 实测可应用。R35 结论继续沿用。

### 第 6 轮（SHA 7f61243e）中止后修正：util.c BSD statfs 假设

第 6 轮 0003 生效（linuxattr 首错消除），编译推进到 util.c 后死于
`lib/util.c:592: variable has incomplete type 'struct statfs'` +
`use of undeclared identifier 'MNT_LOCAL'`。根因：xar_optimal_io_size_
at_path()（macports-port 分支移植层新代码，Apple/macports 环境之外
未测过）无平台守卫直接使用 BSD 专属 statfs 语义——f_iosize/f_flags
与 MNT_LOCAL 宏均非 POSIX（musl 只实现 statvfs）；util.c 已 include
的 sys/mount.h 在 musl sysroot 里存在但不提供这些符号。不伪造宏
（musl statfs 布局不保证字段存在，语义错误风险）；修复：新增
patches/0004-util-io-size-nonapple.patch——statfs 探测段 #ifdef
__APPLE__ 守卫，非 Apple 直接返回函数自身 fallback 1024*1024（1MiB
本是代码起点；调用点 archive.c:631/io.c:125 仅 I/O 块大小优化，非
功能必需）。

## 留给 MateBook 的验证项

1. R35：上列 4 个依赖 conan download 制品确认。
2. conan create + conan test 完整跑通（configure → make -j1 → build()
   自检 → make install → 消费者测试）。
3. 关注点（失败时按下列顺序排查）：
   - openssl 3.5 下 hash.c 补丁编译：若 EVP_DigestInit 等 deprecated
     声明触发额外警告，属预期；若 OpenSSSL_add_all_digests 链接失败
     （3.x 保留为兼容符号，预期无问题），记录首个真实错误。
   - --build/--host 绕开路线：确认 configure 输出 abi=elf（case 命中
     *-*-linux*）；若出现 "can not detect the size of your system's
     dev_t type" 说明编译探测未走通（应不会，AC_CHECK_SIZEOF 编译期）。
   - xml2-config shim：--version 解析为 2.15.3.1 → configure 判定
     libxml2 >= 2.6.11 应通过；AC_CHECK_HEADER libxml/xmlwriter.h 依赖
     AutotoolsDeps 注入的 CPPFLAGS。
   - make -j1：根 Makefile 的 lib_static/src_all 两线；若 .d 依赖文件
     生成规则（-MM）在 OHOS clang 下有问题，记录首个真实错误。
   - 消费者断言 6 的 "sha1"：TOC 默认校验和 SHA1（上游语义）；若
     dump-toc 输出大小写不同，grep -qi 已容错。
4. `ohc-run.py finish xar 1.8.0.498 built` → W4 审计（不跑 submit）。

### 第 7 轮（SHA 80528fce5）补充修正：sysroot 无 fts(3)

0004 生效（lib 阶段全绿：libxar.a 产出并 ranlib，上轮首错消除），
新首错在 CLI 编译：`src/xar.c:39:10 fatal error: 'fts.h' file not
found`。根因：OHOS SDK sysroot（musl）不提供 fts(3)（BSD 文件树遍历
API，sysroot 无 usr/include/fts.h，真机确认）；使用点唯一——
src/xar.c 的目录递归扫描（fts_open/fts_read/fts_close +
FTS_PHYSICAL|FTS_NOSTAT|FTS_NOCHDIR(±XDEV)、FTS_DP、fts_path/
fts_info，约 177-281 行），是 xar -c 枚举输入文件树的核心路径，无
编译期开关；libxar.a 不含 fts 依赖。

修复（patches/0005-fts-vendored.patch，portability）：制品仓无 fts
包（为单工具新增依赖任务过重），vendor void-linux/musl-fts（NetBSD
fts.c 1.48，BSD 许可证随文件保留）：
- 新增 src/fts.h（原样）与 src/fts.c（仅两处机械改动：去掉 autotools
  `#include "config.h"`——全部 HAVE_* 条件回退可移植默认，musl 有
  dirfd、dirent 无 d_namelen、MAX 回退激活；`<fts.h>` 改 `"fts.h"`
  同名本地头）；
- src/Makefile.inc.in 的 XAR_SRCS 加 fts.c（走既有 %.o/%.d 模式规则）；
- src/xar.c `#include <fts.h>` → `#include "fts.h"`。
glibc 平台本地对象遮蔽 libc 同名符号，musl 平台补齐缺失；库本体与
消费者测试路径不受影响。Windows 级验证：patch -p1 dry-run/apply
幂等，与手工 vendor 树逐文件 diff 零残差；fts.c 的真机编译属 MateBook
复验项（Windows 无 musl 环境不预演）。

### 第 11 轮（SHA b80c23e9 第 10 轮验证中止后处置）：三层根因链修复

第 10 轮进展：0005 补丁 export+apply 全过、lib 全量编译+libxar.a 产出
（fts 阻塞解除），死在 src 链接层。MateBook 在 conan 缓存探针
（probe4-9）完成三层递进诊断并端到端验证修复方案，Windows 按落地
清单实施：

1. 层 1 头文件解析（create 首错 src/xar_internal.h:14 'xar/xar.h'
   not found）：构建树头是扁平 include/xar.h，<xar/xar.h> 是安装后
   布局；src/xar_internal.h 的引号分支需上游全树无定义点的
   XARSIG_BUILDING_WITH_XAR。配方修复：configure 期 CPPFLAGS 追加
   -DXARSIG_BUILDING_WITH_XAR -Ilib -Iinclude（Makefile.in 以
   'CPPFLAGS := @CPPFLAGS@' 赋值压过 make 期 env 注入，必须烘进
   @CPPFLAGS@ 才能同时覆盖 lib/src 编译规则；-Iinclude 补齐
   xar_internal.h/filetree.h 的 "xar.h" 解析，比探针报告多列一项，
   多余 -I 无害）。
2. 层 2 aarch64 char 缺陷（probe7 暴露，被层 1 掩盖）：src/xar.c:913
   'char command = 0, c;'——aarch64 char 无符号，getopt_long 返回
   -1 截断为 (char)-1=255，循环守卫恒真，-c/-x/-t 全落 usage/
   exit(1)，clang -O2 把归档/提取/fts 逻辑当死代码删除（链接"成功"
   、--version 正常，表象极具欺骗性）。0006 补丁改 int。
3. 层 3 0005 链接缺口（层 2 修复后暴露）：fts.c 进编译不进链接，
   fts_open/read/close undefined。0006 补丁在 src/Makefile.inc.in
   两条模式链接规则补 @objroot@src/fts.o 前置。

patches/0006-cli-char-int-and-fts-link.patch（bugfix，sha256
e88afc52…）hunks 对准 0005 应用后状态生成；Windows 级验证：原始
tarball（sha256 9cee4f80… 与 conandata 一致）重新解包，0001→0006
全序 dry-run+apply 全过，终态三项修复齐备、fts.c/fts.h 就位。探针
实证：make exit=0、-czf→-tf→-xf→cmp 往返全绿、nm src/xar 含
fts_open 而 lib/libxar.a 无 fts 符号。新 SHA 需 MateBook 全量复验：
create → test → finish → 审计。

### 第 13 轮（SHA 59b7a97a 复验死于 src 链接）：0006 补链接 recipe

MateBook 对 59b7a97a 复验：交接核对全过、0001–0005 层 1/层 2 无回退
（CPPFLAGS 三追加项可见、lib+src 编译零 xar/xar.h not found）、
src/fts.o 已编译、构建树 Makefile.inc 前置确有 fts.o——仍死在
ld.lld undefined fts_open/read/close（src/xar.o:main）。

第 12 轮新事实（实机构建首次证伪 probe9 结论）：GNU make 模式规则
recipe 是 `-o $@ $<`（$< = 首前置 xar.o），**前置列表只影响触发条件、
不进入命令**——0006 hunk 2 只补前置没改 recipe，fts.o 从未参与链接。
Makefile.inc.in 共 4 条链接 recipe（xar/ixar × RPATH ifeq 两分支，
:41/:43/:57/:59），0006 一条都没改。

修复（MateBook 探针实证的最小方案）：0006 hunk 2 扩为 6 处——两条
模式规则前置保持不变，4 条链接 recipe 在 `$<` 后显式追加
`@objroot@src/fts.o`。conandata 0006 sha256 更新为 c4bfbae9…（补丁
重生成：原始 tarball 重新解包 → 0001–0005 双树应用 → patched 树加
4 处 recipe 修改 → diff 重生成，0001→0006 全序 dry-run+apply 过，
终态树逐字节一致）。

探针已实证重链命令（src/xar.o + src/fts.o + libxar.a）LINK_OK 零
undefined、往返自检全绿。影响构建 → 新 SHA 需 MateBook 全量重走
create → test → finish → 审计。

### 第 14 轮（SHA f800552f 复验：链接层首次全实证；自检缺 out 目录一行修复）

MateBook 对 f800552f 复验：**层 3 链接复核首次全实证通过**——实际
链接命令行含 fts.o（-o src/xar src/xar.o src/fts.o … 与 -o src/ixar
同型，与第 12 轮探针预测一致）、零 undefined、nm src/xar fts_* 已
解析、nm libxar.a 零 fts 符号；层 1（CPPFLAGS 三追加项、零
xar/xar.h not found）、0001–0005、R35 四依赖均不回退。

新阻塞（构建首次走到自检段，此前 11 轮从未触达）：build() 往返
自检只创建了 hello.txt/payload.bin，从未创建提取目标目录 out，
`xar -xf st.xar -C out` 对不存在目录直接 "Unable to chdir to out"
exit 1。探针证实唯一缺口：补 mkdir out 后 EXTRACT/CMP×2/-tf 全绿，
且 make install rc=0、安装后 bin/xar 正常——归档管线与安装路径均
真实可用，配方只缺一行。

修复：build() 创建 selftest 目录后补
os.makedirs(os.path.join(work, "out"), exist_ok=True)。影响构建/
门禁 → 新 SHA 需 MateBook 全量重走 create → test → finish → 审计。

### 第 15 轮（SHA 79abebff 复验：自检修复确认过、install 过；消费者 2/6 —— 测试脚本 create 误用 -C）

MateBook 对 79abebff 复验：本轮唯一修复点真机确认——-xf -C out 不再
报错、往返 cmp×2 过、make install rc=0（include/lib/bin/man 全装）；
链接行含 fts.o、层 1 CPPFLAGS、0001–0006 apply 全部零回退。

消费者 2/6（#1 --version、#2 创建 rc=0 过；#3–#6 连锁失败）。根因
证据链闭合（上游原生语义，非补丁引入）：xar.c 全文件仅 extract
路径一处 chdir（:366），create 路径无；help 原文 "-C <path> On
extract, chdir to this location"——**上游 -C 仅 extract 生效**；
探针 A 用 -C create 复现出与消费者逐字一致的失败签名（Error adding
file → 空归档），探针 B 用 subshell cd 后 create 全绿——工具本体
无缺陷，纯测试脚本误用。

修复（test_xar.sh）：#2/#5 的 create 调用去掉 `-C "$TMP/data"` 改
subshell cd（extract 的 -C 为合法语义保留）；#2 断言顺带加强
（stderr 必须为空，消除本轮暴露的 rc=0 假通过）。另按审计预检建议
补全 manifest 0006 条目描述（4 条链接 recipe $< 追加、仅补前置无效
机制半句）。Windows bash 模拟（fake xar 遵守 -C 仅 extract 语义）：
#1/#2/#3 过，#2 的 stderr 空断言生效。新 SHA 需 MateBook 全量重走
create → test → finish → 审计。
---

**编译结束**: 2026-09-29 00:20
**最终状态**: built
