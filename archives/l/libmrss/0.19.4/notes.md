# libmrss 0.19.4 适配笔记

## 编译环境
- 构建系统: autotools（tarball 带预生成 configure，但 NEWS 缺失需
  autoreconf 自举处理）
- 编译日期: 2026-09-10
- 编译器: clang/clang++
- 状态: built
- 本机即 OHOS aarch64（HarmonyOS HongMeng Kernel），原生构建，不使用 --build/--host

## 编译步骤（conan create 全流程）
```bash
conan create . -pr:h=~/.conan2/profiles/ohos-aarch64-local \
               -pr:b=~/.conan2/profiles/ohos-aarch64-local --build=missing
# build() 内部依次：
#   0) touch NEWS（tarball 缺实体文件，automake required file 规避）
#   1) autoreconf -fi（conan automake/1.18 + libtool/2.5.4 + autoconf/2.72
#      闭包，PERL=perl PERL5LIB=<automake share>:<autoconf share> 统一解释器；
#      ACLOCAL_PATH 注入 pkgconf 的 pkg.m4 + libtool 的 libtool.m4）
#   2) E007 变换（配方内纯 Python 复刻 scripts/patch-autotools-ohos.pl）
#   3) ./configure --disable-static --enable-shared（原生 OHOS 路径；
#      经 _build_env：绝对路径 bash + PATH 补 /bin + LD_LIBRARY_PATH +
#      LDFLAGS 剥 libnxml -L + NXML_LIBS/LIBS 指向无 .la 链接目录）
#   4) make（CPPFLAGS 补 -I<build>/src：out-of-tree 时 mrss.h 在构建树）
#   5) make check（上游 1 项正式测试 test/new，纯离线）
#   6) 单独构建并运行 noinst 示例 parser/write/time/search
#   7) make install（同样经 _build_env，规避聚合 conanbuild 的坏 CONFIG_SHELL）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | autoreconf 报 `Makefile.am: error: required file './NEWS' not found` | GitHub tag 归档不含 NEWS 实体文件（上游仓库无此文件），Makefile.am 未声明 `AUTOMAKE_OPTIONS = foreign`，automake 对非 foreign 包强制要求 NEWS/README/AUTHORS/ChangeLog 存在（其余三个 tarball 已有） | 自举前 touch 空 NEWS 文件；属构建系统引导文件缺失，不改源码逻辑。全库查重 0 命中（真实新缺口，登记 DRAFT-6053） |
| 2 | conan 闭包 config.guess 不识别 HarmonyOS | automake/1.18 + libtool/2.5.4 闭包携带 2024-07-27 版脚本（HarmonyOS 0 命中），autoreconf -fi 覆盖进源码树（tarball 自带的也被覆盖） | 配方内纯 Python 复刻 E007 变换（HarmonyOS/* case、__OHOS__ LIBC 探测、ohos config.sub 条目），打在 autoreconf 之后；config.guess 原生输出 aarch64-unknown-linux-ohos 后再 configure |
| 3 | configure "cannot run C compiled programs" → 误判交叉编译 | AC_CHECK_LIB(curl) 要运行 conftest，conftest NEEDED libcurl.so 但无 rpath/LD_LIBRARY_PATH 时退出码 127 | generate() 生成 ohos_env（LD_LIBRARY_PATH 前置 curl libdir），conftest 正常运行 |
| 4 | 包内 .so 的 RUNPATH 携带宿主机 conan 缓存绝对路径 | libnxml 包带 .la：libtool 对 `-L<libnxml libdir> -lnxml` 做 libdir 硬编码（curl 包无 .la 从不触发；与 -Wl,-rpath 无关） | 链接期规避，见 #13 |
| 5 | 包内 .so 的 DWARF comp_dir 含 /storage/... 绝对路径 | 编译目录在宿主家目录下 | -ffile-prefix-map/-fdebug-prefix-map/-fmacro-prefix-map（libgcrypt/1.12.2 同款）把 source/build 目录映射为 "." |
| 6 | PKG_CHECK_MODULES(nxml>=0.18) 找不到 nxml.pc | PkgConfigDeps 生成的是依赖包的 pc，libnxml 包内 pkgconfig 名为 nxml | PkgConfigDeps + AutotoolsDeps 双通道注入；make check 与链接均通过 |
| 7 | L0o 门禁误报风险 | `self.dependencies["curl"]` 裸名带引号会被当成外部 curl 命令调用 | 依赖访问统一 `self.dependencies.direct_host["curl/8.15.0"]` 完整 ref 写法（DRAFT-6052 复用） |
| 8 | configure 首行 re-exec $CONFIG_SHELL 退出 127 | profile buildenv 的 CONFIG_SHELL=/data/service/hnp/bin/bash 本机不存在；且 conanbuild 聚合时 conanbuildenv 脚本在自定义 env script **之后** source（后写覆盖），generate() 的 env script 与 env="conanbuild" 参数都无法覆盖 | _build_env()：绕过 Autotools 封装，自行 source conanautotoolstoolchain.sh + conanautotoolsdeps.sh 取变量，再强制 CONFIG_SHELL/SHELL=绝对路径 bash（_which_bash 定位；裸 `bash` 会让 libtool wrapper 生成非法 shebang `#! bash`，见 #12） |
| 9 | autoreconf 报 `PKG_CHECK_MODULES ... syntax error near unexpected token NXML` | configure.ac 用 PKG_CHECK_MODULES(NXML, nxml>=0.18)，tarball 与 conan automake/libtool 闭包都不带 pkg.m4 | tool_requires pkgconf/3.0.5；autoreconf 命令 ACLOCAL_PATH 注入 pkgconf 的 share/aclocal（E058 同类，abiword 先例），同时拼上 libtool 包的 libtool.m4 路径（否则 AC_PROG_LIBTOOL possibly undefined——os.environ 不含 env script 里的 ACLOCAL_PATH） |
| 10 | configure 阶段 id/od 等基础工具 127 | 本会话 PATH 不含 /bin（OHOS /bin→/system/bin 符号链接） | _build_env 里 PATH 追加 /bin:/system/bin |
| 11 | test/*.c 编译报 mrss.h 不存在 | mrss.h 由 mrss.h.in 生成于**构建树**，上游 AM_CPPFLAGS 只 -I$(srcdir)/../src（源码树），out-of-tree 构建找不到 | make / make check / 示例构建统一传 CPPFLAGS='-I<build>/src -I<src>/src' |
| 12 | make check 报 test-driver bad interpreter（exit 126） | libtool 程序 wrapper 的 shebang 取 CONFIG_SHELL | CONFIG_SHELL/SHELL 一律绝对路径（并入 #8） |
| 13 | 包内 .so RUNPATH 硬编码（真正根因与最终方案） | libtool 对带 .la 的依赖做 -L libdir 硬编码；而 **OHOS lld 自动嵌入 .codesign 段且 musl 加载器校验：链接后改任何字节（含 .dynamic 段清 RUNPATH）都令签名失效**——实测把 DT_RUNPATH d_val 改 0/6 均拒载、恢复原值即 PASS；曾试绝对 .so 路径 + -Wl,--no-as-needed，但 libtool 会把显式 .so 路径吞出链接行 | 全部在链接期规避：_nxml_link_dir() 把 libnxml.so(+.so.0 链接)复制到构建树内**无 .la** 目录，NXML_LIBS/LIBS 指向它（libtool 无 .la 不硬编码、DT_NEEDED 正常记录）；LDFLAGS 剥除 libnxml 的 -L；产物无 DT_RUNPATH 且 .codesign 有效 |
| 14 | test_package 运行 127 | conanrun 聚合 env 不带依赖 libdir；包内 .so 按规范无 RUNPATH，运行查找需显式路径 | test_package 内 Environment 显式 LD_LIBRARY_PATH：被测包 libdir + libnxml + curl（direct_host 完整 ref） |

## NEWS 缺失查重证据（DRAFT-6053 判定）

- graph 全库（含 error-patterns、musl-compat 等知识库）搜
  `required file.*NEWS|touch NEWS|NEWS not found`：0 命中
- 当前分支 knowledge/drafts/ 18 个草稿：0 命中
- libnxml 分支 DRAFT-6049~6052（perl 双 arch / 远端点文件 / L0o curl /
  死域名）：均与本缺口无关
- 复现：fresh 解包 tarball → autoreconf -fi → 立即报
  `Makefile.am: error: required file './NEWS' not found`，exit 1
- 规避后：autoreconf 成功、configure 生成 17000+ 行、make 全通过

## 依赖定性（实测证据）

| 依赖 | 定性 | 证据 |
|------|------|------|
| libnxml/0.18.5 | 库依赖 | configure PKG_CHECK_MODULES(NXML, nxml>=0.18) 强制；mrss_parser.c/mrss_download.c 直接调用 nxml_* API；libmrss.so NEEDED libnxml.so.0 |
| curl/8.15.0 | 库依赖 | configure AC_CHECK_HEADER(curl/curl.h)+AC_CHECK_LIB(curl,curl_version) 强制；mrss_download.c 链接 curl_easy_*；libmrss.so NEEDED libcurl.so |
| automake/1.18, libtool/2.5.4, autoconf/2.72 | 工具依赖 | 仅自举阶段使用（tool_requires） |

- libnxml/0.18.5 发布状态：ohpcd 远端未发布；本地 conan 缓存已有完整
  二进制包（AArch64 ELF、SONAME libnxml.so.0、NEEDED libcurl.so、
  含 nxml.h 与 nxml.pc），为 feat/libnxml-0.18.5 分支的构建产物，
  可直接被 libmrss 的 conan create 解析复用（--build=missing 命中）
- curl/8.15.0：ohpcd 已发布（curl/8.15.0、curl/8.15.0.1）

## 上游测试盘点与执行

| 类别 | 名称 | 处理 | 结果 |
|------|------|------|------|
| 正式测试（automake TESTS） | new | 原样运行（纯离线：mrss_new + mrss_set 全量 flag + mrss_write_buffer 往返 + mrss_free） | PASS |
| noinst 示例（非测试） | parser | 单独构建+运行（本地 127.0.0.1 HTTP feed + 文件数据源） | 退出码 0，输出正确 |
| noinst 示例（非测试） | write | 单独构建+运行（feed.xml → out.xml 往返） | 退出码 0，输出正确 |
| noinst 示例（非测试） | time | 单独构建+运行（本地 HTTP feed 的 last-modified 查询） | 退出码 0，输出正确 |
| noinst 示例（非测试） | search | 单独构建+运行（文件数据源 tag 检索） | 退出码 0，输出正确 |

- 上游 1/1 正式测试真实运行（make check，非 skip）
- 上游无正式测试网络依赖：test/new 纯离线，无需远端 fixture
- 示例程序明确不冒充正式测试，单独验证并留 HMBS_EXAMPLE_* 证据行
- HMBS_UPSTREAM_TEST_RESULT 证据行：{"status": "passed", "discovered":
  1, "executed": 1, "passed": 1, "failed": 0, "skipped": 0, ...}

## 消费者测试（1/1）

test_package/test.c：Conan 安装后的 include/mrss.h + lib/libmrss.so，
内联 RSS fixture 真实调用 mrss_new / mrss_set / mrss_parse_buffer /
字段断言（channel title + 2 item title）/ mrss_write_file /
mrss_parse_file 回读 / 非法 XML 拒绝 / mrss_free，编译、链接、运行、
断言全部通过（"ALL PASS"）。

## 鸿蒙特有测试（1/1，tests/ohos-libmrss-consumer/run_ohos_test.py）

六项硬检查全部通过（OHOS-TEST-RESULT: PASS 6/6）：
- A. 包内 libmrss.so.0.19.4 为 ELF64 / AArch64 / ET_DYN
- B. 含 OpenHarmony .codesign 段（工具链注入）
- C. SONAME=libmrss.so.0；NEEDED 含 libnxml.so.0；无 RPATH/RUNPATH
- D. 二进制内无宿主机绝对路径（/storage/、/home/、/Users/、/tmp/libmrss 等）
- E. OHOS 环境实际编译并链接包内库（pkg-config 或显式 -I/-L）
- F. OHOS 环境实际运行真实 RSS 解析并校验结果（channel/item 字段断言）

## SONAME 推导

- configure.ac：`libmrss_version_info = 19:4:19`（minor:micro:minor）
- libtool -version-info current:revision:age = 19:4:19
- SONAME = libmrss.so.$((current-age)) = libmrss.so.0
- 实际构建产物：libmrss.so.0.19.4 / libmrss.so.0 / libmrss.so，
  readelf SONAME=libmrss.so.0，与推导一致

## 交付物

| 文件 | 说明 |
|------|------|
| include/mrss.h | 公共头（自有类型，不透传 curl/nxml 头） |
| lib/libmrss.so.0.19.4 + .so.0 + .so | 共享库（ELF64 AArch64，带 .codesign） |
| lib/pkgconfig/mrss.pc | pkg-config 元数据（Requires: nxml） |
| COPYING | LGPL-2.1-or-later 许可证 |

## 注意事项

- 本机即 OHOS（uname: HarmonyOS HongMeng Kernel 1.12.0 aarch64），原生构建；config.guess 补丁后原生输出 aarch64-unknown-linux-ohos，不需要也不能用 --build/--host 绕过
- 系统 automake 1.16.5 在 PATH 序在前，自举必须显式 tool_requires conan automake/1.18（仓库约定）
- 示例程序的本地 HTTP 服务在配方内以线程起 python http.server（127.0.0.1:18081），随 conan create 进程退出
- conan create --build=libmrss/* 全新构建 CREATE=0；重跑时包缓存命中会跳过 build() 的测试输出，需强制重建才会重现 HMBS 证据行
