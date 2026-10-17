# tcpflow 1.6.1 适配笔记

## 基本信息

- 平台库名: tcpflow
- 上游项目: simsong/tcpflow (https://github.com/simsong/tcpflow)
- 上游 tag: tcpflow-1.6.1 (2021-02-19 发布)
- 官方源码: https://github.com/simsong/tcpflow/archive/refs/tags/tcpflow-1.6.1.tar.gz
- SHA256: c1c88513473e12011c0c00bba88dd02013ea3b813b08088f250cbf82b8f42358
- 许可证: GPL-3.0 (COPYING)
- 语言: C++ (77%) + C, autotools 构建系统 (configure.ac + bootstrap.sh)
- 产物: bin/tcpflow (命令行工具) + doc/tcpflow.1 手册页

## 关键适配决策

### 0. autoreconf 生成文件处理：configure/config.status 的 umask 077→022 运行时替换

GitHub archive tarball 无预生成 configure，`build()` 中 `autotools.autoreconf()`
自举后，对生成的 configure/config.status 做最小运行时替换（conanfile.py
build() 内 glob 递归查找 `**/configure`，仅当含 `umask 077` 时替换为
`umask 022`）。根因（E175/E046）：setgid/HMDFS 下 `(umask 077 && mktemp -d
./confXXXXXX)` 会创建 2700 权限目录，config.status 写入 subs1.awk 时
Permission denied。替换必须发生在 autoreconf **之后**（autoreconf 会重新生成
configure，改早了被覆盖）。该处理与已合入先例 argp-standalone/1.5.0 逐字一致
（同属"GitHub archive 无 configure + autoreconf 自举"场景），非 sed 改上游
源码，不产生 .patch（生成文件补丁会被 autoreconf 覆盖、不可复现）。

### 1. submodule 源码合并（http-parser）

官方 GitHub release tarball **不包含 git submodule 内容**：`.gitmodules` 声明了
`src/http-parser`（https://github.com/simsong/http-parser.git），但 tarball 中该
目录为空（0 个文件）。`src/Makefile.am` 引用 `http-parser/http_parser.c`，因此
直接构建必然失败。

方案（复用 E150 manual-download 模式 + aws-crt-cpp submodules 先例）：
- conandata.yml `sources.submodules` 声明固定 commit `87e395602053` 的独立源码包
  (SHA256 2c7186be...)，在 `source()` 中解压合并到 `src/http-parser/`。

### 2. autoreconf 自举

GitHub archive tarball 无预生成 configure（autoreconf 产物不进版本库），
`build()` 中检测到 configure 缺失时执行 `autotools.autoreconf()`。
tool_requires: automake/1.18 + libtool/2.5.4（制品仓已发布）。

### 3. 依赖（configure.ac 强制）

- zlib (AC_MSG_ERROR 缺失) — zlib/1.3.1
- openssl (libssl/libcrypto，AC_MSG_ERROR 缺失) — openssl/3.5.6
- libpcap (pcap_lookupdev，抓包核心) — libpcap/1.10.6
- boost (interval_map/interval_set，AC_MSG_ERROR 缺失) — boost/1.84.0

可选且未引入：cairo 系 netviz（--enable-cairo=false）、wifi 解码（--disable-wifi）、
lightgrep/tre/regex。

### 4. getpwuid NULL 保护补丁（SIGSEGV 根因修复）

默认 report.xml（DFXML）生成时，`dfxml_writer.cpp:476`
`xmlout("username",getpwuid(getuid())->pw_name)` 在 uid 无 /etc/passwd 条目
（OHOS 容器/CI 常见）时 getpwuid() 返回 NULL → 空指针解引用 → SIGSEGV
（Signal 11，exit 139；report.xml 精确截断在 `<uid>` 之后）。

证据链：report.xml 截断位置 + 最小 C 程序证实 getpwuid(20020084)==NULL +
ASan Debug 构建同点崩溃。上游 main 分支（截至 2026-08）476 行未修复；
上游 commit c125d859db7d（PR #260）的 opt_enable_report=false 仅是 `-c`
console 模式行为调整，非崩溃修复。

修复：`patches/0001-src-be13_api-dfxml-src-dfxml_writer.cpp.patch`
（getpwuid() 返回值 NULL 保护，最小 1 处、可重放、幂等）。修复后默认
report.xml 正常生成，用户无需任何配置，核心流重组不受影响。

### 5. 平台语义

生产 tcpflow 保持真实网络/抓包语义：不做 mock、无隐藏环境变量、无伪造成功路径。
实时抓包依赖 CAP_NET_RAW（受限于运行环境权限），但离线 pcap 解析（-r file.pcap）
是完整可测的核心工作流，上游测试全部基于离线 pcap。

## 构建实验记录

- bootstrap.sh 需要 automake（本机缺失 → 使用本地 automake-1.18 + PERL5LIB 修复，验证 E116 模式）
- configure 原生环境缺 openssl 头 → 由 Conan 配方 requirements 提供
- http-parser 固定 commit tarball 内容与 src/Makefile.am 引用的 8 个文件全部匹配

## 测试

- 上游 make check: 5 个 SH_TESTS (test1.sh test-pdfs.sh test-multifile.sh
  test-iptree.sh test-chroot.sh)，全部基于离线 pcap 文件；
  审计后分类 total=5, passed=1, failed=1 (optional netviz/cairo 未启用),
  skipped=3 (缺外部 nitroba.pcap/2013-httpxfer 大 pcap/root)
- test_package 夹具 test1.pcap：由配方 package() 从上游源码
  （tests/test1.pcap，SHA256 41cc8c96a2502fd6adb5f4498950264f79f7cbb19afc02e094c5105b32b19668，
  7047 字节）复制到包内 test/fixtures/，test_package 经 package_folder 定位；
  不携带二进制进入 PR diff（避免 GitCode PR .diff 缺失二进制数据导致 CI
  checkout-pr 阶段 git apply 失败）
- 详见 test_package/MANIFEST.yml
---

**编译结束**: 2026-08-15 15:28
**最终状态**: built
