# chinadns-c 1.3.2 适配笔记

## 编译环境
- 构建系统: autotools（上游 autogen.sh 流：configure.ac + Makefile.am，tarball 无 configure）
- 编译日期: 2026-09-07
- 编译器: clang 15.0.4 (OHOS SDK 26.0.0.18)
- 状态: built
- 平台: aarch64-unknown-linux-ohos (HarmonyOS)
- 依赖: 仅 libc（无 Conan 依赖，W0 通过）

## 源码获取
- URL: https://github.com/clowwindy/ChinaDNS-C/archive/refs/tags/1.3.2.tar.gz
- SHA256: c7ee94f84844069a1c2aa240c9468ff6567d67e42e5a419db936b1d5ae831532
- tarball 顶层目录: ChinaDNS-1.3.2

## 上游结构核验
- 上游 master 分支是 autogen.sh 流（aclocal && automake && autoconf），
  tag 1.3.2 tarball 只有 configure.ac/Makefile.am/config.h.in，
  **无预生成 configure**
- src/Makefile.am: bin_PROGRAMS = chinadns; chinadns_SOURCES = chinadns.c local_ns_parser.c
- 顶层 Makefile.am: SUBDIRS = src; dist_data_DATA = iplist.txt chnroute.txt
- configure.ac 依赖检查: AC_CHECK_LIB(resolv, res_query) —— OHOS 上通过（见下）
- configure.ac **无 AC_CANONICAL_HOST/BUILD** → configure 不调用 config.guess/config.sub
  （仅在 aux dir 存在这两个文件时才用）→ 无需 config.guess/config.sub 补丁

## 编译步骤（探索期实测）
1. 本机补 automake 1.16.5（hnp 只有 autoconf 2.72 无 automake；源码
   ./configure --build=aarch64-unknown-linux-gnu + make + make install 到
   $HOME/tmp/automake-inst，config.status 需先修 umask 077→000 才能在
   HMDFS 跑过）
2. sh autogen.sh（用上述 automake + 系统 autoconf 2.72）生成
   configure/Makefile.in/src/Makefile.in/aclocal.m4 + compile/install-sh/
   missing/depcomp（automake --add-missing 装的是绝对路径符号链接，
   快照复制时 follow_symlinks=True 解引用为真实文件）
3. 快照 configure 内 umask 077→022（E129 HMDFS；c-algorithms 0003 同款）
4. mkdir build && cd build && ../configure --build=aarch64-unknown-linux-gnu
   --host=aarch64-linux-ohos CC=clang
5. make -j1（OHOS 禁 mkfifo jobserver）
6. make install DESTDIR=staging → bin/chinadns + share/{iplist.txt,chnroute.txt}

## 实测验证（本机 aarch64 musl 环境）
- chinadns -h → usage 全文输出，rc=0 ✅
- chinadns -V → "ChinaDNS 1.3.2"，rc=0 ✅
- chinadns（无参数）→ 尝试 bind 0.0.0.0:53 报 Permission denied
  （沙箱无特权端口，属预期——程序逻辑真实运行）✅
- file src/chinadns → ELF 64-bit arm64, dynamic (/lib/ld-musl-aarch64.so.1) ✅
- 上游 6 个 dig 集成测试（test.py 移植 Python 3）→ 6/6 通过 ✅
  （2026-09-11 conan create 实测：google.com/facebook.com/twitter.com/
  taobao.com/www.facebook.com A 查询 + x_8888 PTR 反查全部 ANSWER SECTION）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 铁律符合性 |
|---|------|------|----------|-----------|
| 1 | tarball 无 configure | 上游 autogen.sh 流发布 | 配方携带 generated-build 快照（本地 automake 1.16.5+autoconf 2.72 生成），CI 无 automake 也可构建（c-algorithms 1.0.0 同款） | ✅ 先例 |
| 2 | config.status 无法创建临时目录 | autoconf 2.72 configure 内嵌 umask 077，HMDFS 0700 目录不可写（E129） | 快照 configure 内 umask 077→022 | ⚠️ R6 改生成文件，但源 configure.ac 不含此代码（autoconf 自动生成），无法从源头改 |
| 3 | config.guess 不识别 HarmonyOS | — | **不适用**：configure.ac 无 AC_CANONICAL_*，configure 不调用 config.guess；--build=aarch64-unknown-linux-gnu 显式三元组即可 | ✅ |
| 4 | AC_CHECK_LIB(resolv, res_query) 探测 | OHOS musl libc.so 直接导出 res_query（nm 确认 T res_query）；sysroot libresolv.a 为 8 字节空 archive（"!<arch>\n"），-lresolv 链接探测仍通过（符号解析自 libc.so） | 无需处理，实测通过 | ✅ |
| 5 | automake --add-missing 装符号链接 | 本机 automake 安装路径是绝对路径符号链接 | 快照复制 follow_symlinks=True 解引用 | ✅ |

## 测试说明（上游 N=6，rule4 对齐 2026-09-11）
- **上游测试口径（审核实测对齐）**：上游 tests/ 下 6 个测试用例文件
  （google.com / facebook.com / twitter.com / taobao.com / www.facebook.com
  为 dig A 查询，x_8888 为 dig -x 8.8.8.8 PTR 反查），由 Python 2 test.py
  驱动（.jenkins.sh CI 入口），统计口径 N=6
- **测试真实运行（boost1.84-serialization 同款 rc 判过手法）**：test.py
  移植为 Python 3 内嵌于 conanfile.py build()（_run_upstream_tests）——
  启动编译产物 src/chinadns -p 15353 -c chnroute.txt -l iplist.txt 转发，
  再对 127.0.0.1:15353 发 DNS 查询验证应答。查询通道双模式：
  dig 可用（试运行验证）→ 原样执行上游 dig 命令（rc=0 且含
  ANSWER SECTION 判过）；dig 缺失（如 CI-021 worker）→ Python 原生
  DNS 客户端（socket UDP + RFC 1035 标准报文）等价查询
  （rcode=0 且 ANCOUNT>0 判过），判定语义一致
- **实测结果**：本机 conan create 6/6 通过（2026-09-11，公网 DNS
  114.114.114.114/8.8.8.8 可达；dig 通道与 python-native 通道均验证
  6/6）；报告留档 build 目录 upstream-tests-report.txt
- **环境限制豁免**：公网 DNS 不可达（网络受限环境）时 SKIPPED
  （环境限制），报告留档，不阻塞构建——集成测试需在线 DNS 为上游
  设计约束（.travis.yml 需 apt-get install dnsutils）；CI-021 实测
  公网 DNS 可达、无 dig，走 python-native 通道真实运行
- test_package 做 API 冒烟（R34：实质依赖被测包）：执行 chinadns -h
  （usage 输出）+ chinadns -V（版本输出 "ChinaDNS 1.3.2"）验证安装布局
  与可执行文件真实可用

## 产物
- bin/chinadns（68KB aarch64 musl ELF）
- share/iplist.txt、share/chnroute.txt（dist_data_DATA 数据文件）
