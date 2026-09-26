# sngrep 1.8.3 适配笔记

任务号：10763（开源鸿蒙PC专项积分赛）｜分支：feat/sngrep-1.8.3｜主理：DS-9（本地形态直跑）

## 编译环境
- 构建系统: autotools（tarball 无 configure，build() 内 autoreconf -fi 自举）
- 编译日期: 2026-09-21
- 编译器: clang 15.0.4（OHOS 工具链，aarch64-linux-ohos）
- 状态: built（conan-verify：G0-G3 PASS、G4 PASS 带告警、L2/L4/L5 框架口径 PASS 实为跳过；制品上传待 release 流水线）
- conan: 2.29.1（OHOS 适配版）；CONAN_HOME=~/tmp/ch/home-DS9-sngrep

## 编译步骤
1. W0 依赖探针（R35 conan download --only-recipe）：libpcap/1.10.6、ncurses/6.5、openssl/3.5.6 配方均已发布；最终依赖面取 libpcap+ncurses（TLS/PCRE/zlib/EEP 经 --without/--disable 全关，见下）。
2. init-build（GitHub 直连不稳 → 官方 codeload.github.com 入口，sha256=794224f4…1b8 与 github.com/archive 同源字节一致，已预置共享 dlcache）。
3. lang-preflight：匹配通过（detected=c，c↔cpp 兼容族，任务声明 cpp）。
4. 原生探索构建全通后固化为配方：autoreconf -fi 自举 → E011/E114 去 umask 077 包裹 → configure（--enable-unicode + 全部可选特性关闭，CPPFLAGS/LDFLAGS 注入 conan 依赖路径）→ make → make check（11/11）→ make install。
5. conan-verify sngrep 1.8.3：G0/G1/G2/G3 PASS、G4 PASS（告警：无法定位包 ID）、L2/L4/L5 框架口径 PASS（实为跳过：无 cache 路径），报告 reports/conan-verify-report.md。

## 上游测试账本（五维口径，AGENTS §10.1）
- `N_static` = **11**：tests/Makefile.am `TESTS = $(check_PROGRAMS)`，test-001..test-011 共 11 个测试程序（test-007 vector 含 10 断言、test-010 hash 含 8 断言，其余为退出码型冒烟）。
- `N_registered` = 11 程序（parallel-tests test-driver）。
- `N_executed` = **11/11 全 PASS**（make check 输出 `# TOTAL: 11 / # PASS: 11 / # FAIL: 0 / # ERROR: 0`；conan create 日志 reports/conan-create.log，同源旁证 reports/w3-local-ci.log）。
- 未执行分类 = 0。
- `N_consumer` = 1（test_package 消费者测试：真实执行被测包安装的 sngrep 二进制，三层断言全部由退出码/输出决定——① `--version` 退出 0 且输出含 "1.8.3"；② `--help` 退出 0 且输出含 "Usage"；③ **功能断言** `-N -I test_package/ipip.pcap`（no-interface，无需终端）解析真实 SIP pcap，断言输出含 `Dialog count: 1`，覆盖 SIP 流重建这一核心能力；1/1 通过，1.8.3 包内实测 maxrss≈5.7MB）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | configure 解析期语法错 `unexpected 'LIBGCRYPT,'`（--without-gnutls 也不可规避） | 工具链缺 pkg.m4 → configure.ac 中**未守卫**的 PKG_CHECK_MODULES([LIBGCRYPT]…) 自举后字面残留进 shell（守卫处正常回落 AC_CHECK_LIB） | patch：libgcrypt 检测段去 pkg-config 化为纯 AC_CHECK_LIB（同族先例 §970/E089 的标准解法是拷 pkg.m4，见 notes 末 B 判定与代价说明） |
| 2 | config.status 报 subs1.awk: Permission denied | E011/E114：HMDFS 下 `umask 077 && mktemp/mkdir` 组合不可写 | patch/配方内去除 configure 两处 umask 077 包裹（保留真实临时目录创建） |
| 3 | conftest 阶段 `clang: no input files` | E386 族：HMDFS 构建目录 + hnp bash 的 SHELL 使 conftest 相对路径失效 | 配方内显式 CONFIG_SHELL/SHELL=/bin/sh 路由 + TMPDIR 指向构建内可写目录（E002：设备 /tmp 只读） |
| 4 | 链接 `undefined symbol: pthread_cancel` | OHOS musl 不提供 pthread_cancel | patch：configure.ac 加 AC_CHECK_FUNCS([pthread_cancel]) 探测，capture.c 以 HAVE_PTHREAD_CANCEL 守卫提供 no-op 兼容（capture_close 先 pcap_breakloop 协同停线程，语义等价） |

## 源码修改（patches/0003-configure.ac.patch + patches/0004-src-capture.c.patch，portability 类，无平台宏；0001-INSTALL/0002-compile 为 autoreconf 自举生成物刷新，无语义变化）
- configure.ac：①libgcrypt 检测去 pkg-config 化；②AC_CHECK_FUNCS 增加 pthread_cancel 探测。
- src/capture.c：新增 HAVE_PTHREAD_CANCEL 守卫的 no-op pthread_cancel 兼容（附注释说明协同关闭语义）。
- 上游测试文件零修改。
- **补丁集构成说明**：`0001-INSTALL.patch` / `0002-compile.patch` 是框架 `finish` 的 `refresh-patch --auto`
  在 autoreconf 自举后按源码树重生成的**辅助脚本版本刷新**（`INSTALL`、`compile` 两个 automake 生成物，
  无语义改动，共 660 行）；它们对构建无实际影响（`build()` 内 `autoreconf -fi` 会重新生成这两个文件），
  保留是为了与框架的补丁生成结果保持一致（移除后重跑 `finish` 会被再次生成）。平台适配的语义改动
  只在前两个：`0003-configure.ac.patch`（去 pkg-config 化 + pthread_cancel 探测）与
  `0004-src-capture.c.patch`（no-op 兼容）。

## 依赖版本
- libpcap/1.10.6（必需，静态）
- ncurses/6.5（unicode 宽字符路径：libncursesw/panelw/formw/menuw，静态）

## 验证结果

```bash
conan create archives/s/sngrep/1.8.3 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
# make check：11/11 passed；test_package 消费者断言：通过
conan-verify sngrep 1.8.3   # G0-G3 PASS、G4 PASS 带告警、L2/L4/L5 口径 PASS（实为跳过）
```

- 上游测试：N_executed=11/11（静态全量 N_static=11，TESTS 注册口径）
- 消费者测试：1/1 passed（sngrep 二进制 --version/--help 断言）
- 已知限制：TLS 解密（gnutls/openssl）、PCRE 正则过滤、zlib 压缩、EEP 远程捕获、logo 编译期特性全部关闭（--without/--disable，均为上游可选增强；如需启用需先适配对应依赖）；交互式 TUI 需真实终端，脚本场景用 -I <pcap> 离线模式。

## 路径 B 判定（create）
- 机制：工具链缺 pkg.m4 时，configure.ac 中**未守卫**的 PKG_CHECK_MODULES 调用自举后字面残留 → configure **解析期**语法错，--without-* 禁用特性不可规避（与守卫处正常回落形成对照）。
- 查重：§970（拷 pkg.m4 进 m4/ 再 autoreconf）与 E089（replace-pkginstalldir，症状不同）为同族/相邻；§970 的解法（拷 pkg.m4）与本条解法（configure.ac 去 pkg-config 化）**不同**，按 §6.2 家族命中四条件之 2 判 **create**。
- 草稿：knowledge/drafts/DRAFT-sngrep-1.8.3-pkg-m4-missing-parse-error.{kv,md}（成对，随本 PR 提交）；关联 Issue：待创建（PRE_CREATE）。
- 替代解法代价（等效性说明）：AC_CHECK_LIB 不注入 -I/版本约束——本包 gnutls 特性整体禁用故该分支不执行、无注入风险；若未来启用 gnutls 构建需自行补 CPPFLAGS（E2186 同类坑），草稿 safety_boundary 已注明。
---

**编译结束**: 2026-09-21 16:22
**最终状态**: built


### CI worker 缺 automake：自举生成物入库（2026-09-25，主理-31）

- 症状：CI #60451（rev a823f4a9）L0/KC/JC 全过后，conan create 在 `autoreconf -fi` 处
  `Can't exec "aclocal": No such file or directory` → autoreconf exit 2（用时 1.8min）。
  本地设备 W3 全绿不可复现——设备 ~/usr/local/bin 有完整 automake 工具链，CI worker PATH
  只有 autoconf（/data/service/hnp/autoconf.org/，FileUtils.pm 能跑）没有 aclocal。
- 根因：上游 github tarball 不带 configure，配方 build() 内 `autoreconf -fi` 自举；该步依赖
  CI worker 未安装的 automake。仓内其它配方均不自举（上游发布带 configure），此坑首例。
- 修法：本地完整复现配方补丁序（0003→0004）后 autoreconf -fi，把生成物
  （configure/aclocal.m4/Makefile.in×4/depcomp/missing/install-sh/test-driver；INSTALL/compile
  已由 0001/0002 覆盖故剔除）做成 patches/0005-autotools-generated.patch（562KB 纯文本），
  build() 删 autoreconf 调用、改为对生成物 chmod 0755（HMDFS 补丁产物无执行位）。
- 验证：五补丁按 conandata 顺序在 pristine 树上全过 + `sh -n configure` 语法过 + 本地
  conan create/conan test 全绿（见下节）。适用边界：任何「配方内自举」型 autotools 包上 CI
  前必须确认 worker 有 automake，否则本地自举入库（M23 同族：CI 与本地工具面差异）。
- 已试失败方案：补发 /rebuild（同处即挂，#60399/#60451 两连）；不做任何环境假设性修补
  （如给 worker 装 automake——无权限且非配方职责）。

- 落地细节补记：①生成物补丁 0005 用动态发现（*.in/configure/aclocal.m4/depcomp/missing/
  install-sh/test-driver 等，config/Makefile.in、src/config.h.in 这类深目录文件极易漏）；
  ②build() 内联 `CONFIG_SHELL=/bin/sh SHELL=/bin/sh`（DRAFT-6487-classads：profile buildenv
  的 hnp bash 对 HMDFS getcwd 必挂，Environment().apply() 压不过 buildenv）；③R49 依赖注入
  必须在 build() 现场以 CPPFLAGS/LDFLAGS 内联前缀生效——generate() 里 tc.configure_args 的
  追加不存续到 build 期（死代码），此前靠设备系统目录的 libpcap 掩盖；④特性旗标
  （--enable-unicode 等 8 项）同属 generate() 死代码，须在 build() 显式重传，否则 unicode
  路径探测纯 -lncurses 必挂（包内只有 libncursesw）。最终：本地 conan-verify G1/G0/G2/G3
  全 PASS + conan test 3/3 断言过。
