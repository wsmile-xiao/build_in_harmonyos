# radlib 2.12.0 适配笔记

## 任务信息
- 任务号: 9966（开源鸿蒙PC专项积分赛-依赖）
- 分支: feat/radlib-2.12.0（worktree ~/qzy/GLM-55-radlib-2.12.0）
- 适配路径: 路径 A（依赖适配）；不走路径 B（判断依据见下）

## 路径 B 判断（2026-09-19）
- 判断依据：本任务为常规 autotools 配方适配（默认零外部依赖），过程中的坑（E007 三元组、E386 shell 路由、clang15 隐式声明、SHA 32 位字宽）均为单库可移植性缺陷的定点修复，不构成可跨仓库复用的新知识（同类 old-autotools/字宽问题已有知识库条目覆盖）。判定：纯路径 A。

## 源码 URL 核查（重要）
- 登记的平台上游 github.com/mteel/radlib 的 tag 2.12.0（git ls-remote 唯一 tag）对应 2014-05-09 的残缺快照：归档仅含 Makefile + dbtest.c 两个文件，无库源码，不可作为 2.12.0 源码。
- radlib 官方发布渠道为 SourceForge（project/radlib），radlib-2.12.0.tar.gz 完整（src/ h/ msgRouter/ debug/ configure 等），sha256=82b98bb5e08a500dea1e4252843b9c772fa1fb67ac8ab89ed64abdd5e22eca66（本机下载与手动 curl 双源一致）。conandata.yml 采用该官方 URL。

## 编译环境
- 构建系统: autotools（发布 tarball 自带 configure，但因 configure/ltmain 版本杂交需 autoreconf 重生成，见下）
- 编译日期: 2026-09-19
- 编译器: clang/clang++ 15（OHOS 工具链，conan profile ohos-aarch64）
- 状态: built（conan-verify W3 通过后更新）

## W0 依赖检查
- 默认构建零外部依赖：configure.in 仅 AC_CHECK_LIB(c, strncpy)、AC_CHECK_LIB(m, exp)；mysql/postgresql/sqlite 支持默认关闭（AC_ARG_ENABLE 默认 false），不引入外部库。
- pthread：radlib 使用 POSIX 线程，OHOS musl 将 pthread 并入 libc，无需单独链接。

## W0b 历史经验
- 归档无 radlib 历史版本，无历史 notes 可迁移。
- 语言预检 lang-preflight: detected_language=c（46 个 .c 文件，100%），与任务语言兼容族，通过。

## 上游测试清点（五维账本，实测口径）
- N_static = 5：test/ 目录下 5 个独立测试程序（sha/radsha.c、multicast/multicast.c、msgRouter/routetest.c、database/dbtest.c、sqlite/dbtest.c）。注意口径：这 5 个程序**未被 automake 注册**（顶层 Makefile.am `SUBDIRS = src msgRouter debug`，test/ 整体在 EXTRA_DIST，无 TESTS/check_PROGRAMS），注册口径为 0；机器人按源码树测试资产实测口径为 5。首版申报按注册口径写 0，被审查机器人判 rule4 少报（实测 5 > 声明 0），已按实测口径上修。
- N_registered = 0（automake 无注册测试；make check 空跑，配方 build() 仍执行该入口）。
- N_executed = 1：test/sha/radsha.c 已在配方 build() 内真实执行——编译链接构建出的 librad，运行 `radsha 256 sha_input.txt` 与 `radsha 1 sha_input.txt` 两种模式，断言退出码 0 且摘要为 64/40 位合法十六进制串（执行记录见 conan-create 日志）。
- 未执行 = 4（逐项分类，见 test_package/MANIFEST.yml 台账）：multicast（无限 RX/TX 循环，无自动退出条件，需人工值守）；msgRouter/routetest（需先手工拉起 radmrouted 守护进程拓扑 + APPLICATION_RUN_DIRECTORY 目录布局）；database/dbtest（依赖 MySQL/PostgreSQL 可选后端，上游默认 --disable）；sqlite/dbtest（依赖 SQLite 可选后端，上游默认 --disable）。
- N_consumer = 1：test_package/test_radlib.c（编译链接 radlib，6 处断言：SHA-1/SHA-256 FIPS 180 向量 3 处 + CRC32/CRC16 3 处）。

## 上游缺陷与修复（aarch64/LP64）
- **SHA 实现字宽错误（已修复，补丁 0001/0003）**：src/radsha.c 按 32 位字设计却使用 unsigned long（LP64/aarch64 上 64 位）。后果：①SHA256_Transform 的 W256=(ULONG*)buffer 按 8 字节步进访问 64 字节缓冲，W256[15] 越界 64 字节砸栈（SIGBUS/SIGSEGV，实测复现）；②全部摘要数学错误（SHA1('abc') 输出乱码 b5977fa8...）。修复：radsha.c 与 radsha.h 中 SHA 段 ULONG 全部改用 uint32_t（ULONGLONG/bitcount 位宽不变），FIPS 180 向量验证通过（SHA1('abc')=a9993e36...、SHA1('')=da39a3ee...、SHA256('abc')=ba7816bf...），上游 radsha 测试两种模式均正常退出。
- 修复前证据：radsha 256 触发 Signal 11/7 core dumped；SHA1('abc') 输出乱码（首轮消费者测试日志）。

## 编译步骤
1. conan create（conan-verify G2）：source() 从 SourceForge 官方 tarball + automake/libtool 官方源码包（build_tools）。
2. build() 内 replace_in_file 修 configure.in 旧宏：AM_CONFIG_HEADER→AC_CONFIG_HEADER、AM_INIT_AUTOMAKE([radlib],[2.12.0])→AM_INIT_AUTOMAKE([foreign])。
3. bootstrap automake/libtool 到私有前缀（worker 缺 host automake、conan perl 在 OHOS 损坏），工具 configure 加 --build 跳过 config.guess 的 HMDFS mktemp 写失败（E011 变体）。
4. `env -u PERL5LIB ... PATH=<私有前缀>/bin:$PATH autoreconf -fi` 全量重生成。
5. 手动调用 configure（conan Autotools.configure() 不支持注入 env）：`env CONFIG_SHELL=/bin/sh SHELL=/bin/sh sh configure <args>`，args 与工具链组合逐字一致。
6. make -j1 → make check（空跑）→ **编译并真实执行上游 test/sha/radsha 测试**（两种模式 + 摘要格式断言）。
7. package()：autotools.install() 后复制 h/*.h 到 include/，删除 *.la。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 首次拉到残缺源码树 | GitHub tag 2.12.0 是 2014 年 2 文件快照 | 改用 SourceForge 官方发布 tarball |
| 2 | configure: cannot guess build type | config.guess 不识别 OHOS 宿主（E007） | 显式传 --build/--host=aarch64-unknown-linux-gnu |
| 3 | 生成的 libtool 脚本语法错误 | 1999 年 configure 搭配 libtool-2.4 ltmain.sh | autoreconf -fi 全量重生成（bootstrapped 工具链） |
| 4 | autoreconf 报 perl Cwd.so 符号缺失 | conan perl 二进制在 OHOS 不可用 | env -u PERL5LIB 剥离 + 私有前缀 automake/libtool |
| 5 | config.status 把 Makefile 生成进 conftest.dir | autoconf 选用 hnp bash，其 getcwd() 在 HMDFS 下挂（E386） | 手动 configure 并 inline 钉 CONFIG_SHELL=/bin/sh |
| 6 | worker 上 autoreconf: aclocal 不存在 | CI worker 无 host automake | conandata build_tools 官方源码包本地 bootstrap |
| 7 | radsysutils.c/radqueue.c: O_RDWR 未定义 | 未包含 <fcntl.h>（musl 无传递包含） | 补丁 0002（radsysutils）；radqueue 由 build() 归一化+插入（CRLF 文件补丁工具会整文件重写） |
| 8 | SHA 摘要乱码 + radsha 测试 SIGBUS/SIGSEGV | SHA 按 32 位字设计但用 64 位 unsigned long（LP64），W256 越界砸栈 | 补丁 0001/0003：SHA 段改 uint32_t，FIPS 向量验证通过 |
| 9 | 消费者无法编译（无安装头文件） | 上游 automake 不安装 h/ 公共头 | package() 复制 h/*.h 到 include/ |

## 源码修改
- patches/0001-src-radsha.c.patch：SHA 32 位字宽修复（见上表 #8）。
- patches/0002-src-radsysutils.c.patch：补 #include <fcntl.h>（见 #7）。
- patches/0003-h-radsha.h.patch：SHA 结构体字宽同步（与 0001 配套）。
- radqueue.c 的 CRLF 归一化与 fcntl 插入在 build() 内完成（见 #7）。

## 依赖版本
- 无外部依赖（libc/libm 由平台提供）；构建期 tool 源码包 automake-1.18/libtool-2.5.4（GNU 官方，仅 build 期 bootstrap 用，不进产物）。

## 验证结果
```bash
python3 scripts/ohc-run.py conan-verify radlib 2.12.0
# G1/G2/G3/G4 + L2/L4/L5 通过后回填：conan create 退出码、
# 上游 sha 测试 2 模式执行通过、消费者测试 6/6 断言通过
```

## 交付物
- librad.a / librad.so（libtool 双态，包默认静态）
- bin/radmrouted（消息路由守护）、bin/raddebug（调试工具，commands.json 已声明）
- include/*.h（radlib 公共 API 头，来自上游 h/）

## 注意事项
- SHA 修复后的摘要与上游 x86 32 位平台输出一致（FIPS 向量），下游可正常使用 radsha.h API。
- test/msgRouter 的 routetest 需多守护进程拓扑，属手工套件，未纳入自动执行。
---

**编译结束**: 2026-09-19 10:58
**最终状态**: built
