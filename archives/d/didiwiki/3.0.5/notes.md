# didiwiki 3.0.5 适配笔记

## 基本信息

- 上游发布名：ciwiki（SourceForge 项目 ciwiki，DidiWiki 的后续分支；3.0.x 起可执行名均为 ciwiki）
- 版本：3.0.5（2024-11-02 发布，ChangeLog 2024-11-04 打包）
- 源码归档：https://downloads.sourceforge.net/project/ciwiki/ciwiki-3.0.5.tar.gz
  （即 https://sourceforge.net/projects/ciwiki/files/ciwiki-3.0.5.tar.gz/download 的
  302 重定向目标；conandata.yml 必须用带 .tar.gz 扩展名的规范直链——conan get() 依赖
  扩展名识别压缩格式，`/download` 结尾的无扩展名文件会被误判为 zip 导致 BadZipFile）
  - Debian 镜像 https://deb.debian.org/debian/pool/main/d/didiwiki/didiwiki_3.0.5.orig.tar.gz 与之字节相同（未重打包）
  - SHA256：290aee7fe2efc8f1c2612b6aff2bb832d3c8129e6fd9dd9e6adbdb02d1f19aef
- license：GPL-2.0-or-later（src 源码头文件声明 GPLv2 "or any later version"；tarball 内 COPYING/LICENSE 为 GPLv2 许可证文本）
- 语言/依赖：纯 C，零外部库（仅 libc）
- 构建系统：autotools（tarball 自带生成的 configure、Makefile.in 与作者构建残留 config.h/config.status 等）
- 产物：`bin/ciwiki`（内建 HTTP 服务器的 wiki 引擎）；另安装 `libexec/notifynewuser.sh` 与 man 手册

## 编译环境

- 平台：OpenHarmony PC aarch64（musl libc）
- profile：ci/conan/profiles/ohos-aarch64（clang 15, os=OHOS, arch=armv8）
- 编译器：/data/service/hnp/bin/clang

## 构建步骤（conan create 自动完成）

1. source()：下载 tarball，解包到临时目录后将唯一根目录内容上移（tarball 成员名带
   "./" 前缀，conan strip_root 只剥 "./" 不上移根目录）；随后清理作者构建残留
   （config.status/config.log/config.h/stamp-h1/各级 Makefile）——conan 为 VPATH
   构建，残留 config.status 会触发 "source directory already configured" 错误。
2. build()：应用 patches/0001-configure-umask.patch 后执行 `./configure && make -j1`。
   - configure 无 AC_CANONICAL_HOST，不需要 config.guess/config.sub 补丁。
   - 不可跑 autogen.sh：configure.ac 使用已废弃的 AM_CONFIG_HEADER 宏，现行 automake 已移除。
   - 生成 Makefile.in/configure/aclocal.m4/config.h.in 均保留，由本次 configure 重新生成其余产物。
3. package()：`make install` 安装 bin/ciwiki、libexec/notifynewuser.sh、man 页到 package 目录。

## 补丁说明

`patches/0001-configure-umask.patch`：configure 创建安全临时目录使用 `umask 077`，
设备默认 umask 即 077，生成的构建文件权限过于严格影响后续步骤（Conan 缓存搬运、
test_package 执行）。放宽为 007，与 dash-shell 0.5.13.2（patches/0003-configure.patch）
先例一致，属 autotools 在该设备上的通用适配。

`patches/0002-fix-stdin-const-assign.patch`：src/ci.c:181 的 `-t` 分支执行
`stdin = freopen(NULL,"r",stdin);`，OHOS musl sysroot 将 stdin 声明为
`extern FILE *const stdin;`，对 const 变量赋值直接编译失败。按 C/POSIX 语义，
freopen 调用本身即完成流的重关联，无需（也不应）回赋，已全平台源码 grep 确认
仅此一处对标准流赋值；去掉回赋后各平台行为不变。

## 上游测试核验（NO_UPSTREAM_TESTS）

- tarball 清单无 tests/、test/ 目录，无 *test*.c 源文件（src/ 仅 ci/http/util/wiki/wikiashtml/wikichanges/wikientries/wikilogin 8 组实现文件）。
- 顶层与子目录 Makefile.am 均无 `TESTS` 变量；无自定义 `check` 目标（顶层仅有 snapshot 目标），`make check` 落到 automake 默认 `check-am: all-am` 空目标。
- configure.ac / configure 无 AC_CONFIG_TEST_DIR 等测试配置。
- 结论：上游零自动化测试，L1 采用 test_package 冒烟（`ciwiki -v` 输出 `CiWiki - version 3.0.5` 且退出码 0，src/ci.c:151）。
- 不做 HTTP socket 冒烟：CI 环境 socket 受限（darkhttpd 1.17 先例），且 `-v` 在进入 wiki_init/http_server 之前即返回（src/ci.c:151-152）。

## 注意事项

- ciwiki 正常运行会在 $HOME/.ciwiki 下写状态；test_package 冒烟使用一次性临时 HOME，不触碰真实用户数据。
- `ciwiki -v`（等价 `--version`）打印版本后立即退出，可直接用于自动化验证。
