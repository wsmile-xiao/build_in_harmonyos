# procps 4.0.7 适配笔记

## 编译环境

- 构建系统: autotools（configure + make）
- 编译日期: 2026-09-04
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，由 Conan 工具链注入，R33）
- 目标平台: OHOS 6.0 / aarch64（armv8），triplet `aarch64-unknown-linux-ohos`
- Conan: 2.29.1（OHOS 适配版），profile = ci/conan/profiles/ohos-aarch64
- 状态: built（conan-verify G0-G4 PASS + W3 L 门禁 pass（L4=warn 已披露），未 upload）

## 编译步骤

1. 前任探索构建（工作树 `$HOME/tmp/builds/procps-4.0.7.work`，staging 树
   `$HOME/tmp/test-install-procps-4.0.7`）：打补丁 → `./configure
   --prefix=/storage/Users/currentUser/usr/local` → `make -j1` → `make
   install DESTDIR=...` → `make check`（8 程序：7 PASS / 1 FAIL / 0 SKIP）。
2. 本轮固化为 Conan 配方：conanfile.py（AutotoolsToolchain + VirtualBuildEnv
   注入 PKG_CONFIG_PATH 指向 conan ncurses/6.6）+ conandata.yml（官方源
   URL + sha256 实算 + 6 补丁）+ test_package（C API 实测 + 二进制输出断言）。
3. `conan create . --build=missing`（default profile，OHOS 设备原生）PASS；
   `ohc-run.py conan-verify` G2 用 ci/conan/profiles/ohos-aarch64 干净构建
   PASS（G0-G4 全过含警告披露，L 门禁见「验证结果」节）。

configure 参数（配方内固定）：`--disable-nls --disable-numa
--without-systemd --with-ncurses` + 静态时 `--enable-static
--disable-shared`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 | 知识 |
|---|------|------|----------|------|
| 1 | strverscmp 未定义（链接 libproc2 失败） | musl libc 无 strverscmp | local/strverscmp.c 补入 libproc2 源列表：0001-Makefile.am.patch + 0002-Makefile.in.patch（对象追加+编译规则） | E534 |
| 2 | configure 不识别平台 | config.guess/sub 无 HarmonyOS 分支 | 0003-config.guess.patch（__OHOS__→LIBC=ohos，*:HarmonyOS:*→aarch64-unknown-linux-ohos）+ 0004-config.sub.patch（ohos-linux case） | E007 |
| 3 | configure 创建临时目录失败 | HMDFS 拒绝 drwx------（umask 077 产物） | 0005-configure.patch 移除两处 umask 077 | E011/E114 |
| 4 | w.c 编译失败（utmpx） | OHOS 无 utmpx | 0006-src-w.c.patch：stat.h include 后 __OHOS__ 下 #undef HAVE_UTMPX_H | E121 |
| 5 | 上游 test_version 失败 | HongMeng 内核版本串非标准 | 环境性失败，不修（见下节定性），build() 中 try/except 记录后继续 | 环境限制 |
| 6 | sourceforge /download 后缀 URL conan 识别不了 | conan 按扩展名选解压器，无 .tar.xz 后缀按 zip 解 → BadZipFile | conandata URL 改为官方直链 https://downloads.sourceforge.net/project/procps-ng/Production/procps-ng-4.0.7.tar.xz（sha256 同文件校验一致 9d2021f4...） | 本轮新增 |
| 7 | make -j2+ jobserver mkfifo 失败 | HMDFS 不允许 FIFO | 全程 make -j1 | 已知 |

## 源码修改

6 个补丁（`patches/`，全部 per-file-difflib 自动生成，conandata.yml 含
sha256）：

1. 0001-Makefile.am.patch — local/strverscmp.c 入 libproc2 源列表
2. 0002-Makefile.in.patch — local/strverscmp.lo 对象 + 编译规则（再生文件）
3. 0003-config.guess.patch — HarmonyOS 平台识别
4. 0004-config.sub.patch — ohos-linux case 分支
5. 0005-configure.patch — 两处 umask 077 移除
6. 0006-src-w.c.patch — __OHOS__ 下禁用 utmpx

另：local/strverscmp.c 为上游自带的 musl 兼容实现（源码 local/ 目录），
本适配仅将其加入 libproc2 编译列表（0001/0002），未新增文件。

生成产物补丁说明（R6 例外）：0002-Makefile.in.patch 与
0005-configure.patch 直接修改 configure 体系的生成产物（Makefile.in /
configure），因目标环境无 autoreconf 工具链无法在本机再生成。0001 已
同步修改源文件 Makefile.am，源/产物保持一致；0005 的两处 umask 077
移除仅存在于生成产物 configure 中（configure.ac 未改动，上游若以
autoreconf 再生成需重打此补丁）。

## 依赖版本

| 依赖 | 版本 | 来源 | 用途 |
|------|------|------|------|
| ncurses | 6.6 | conan ohpcd（静态宽字符） | top/slabtop/watch（ncursesw） |
| gettext/libnuma/systemd | — | 禁用 | --disable-nls --disable-numa --without-systemd |

ncursesw 注入方式：VirtualBuildEnv 附加 PKG_CONFIG_PATH→conan 包
lib/pkgconfig（configure 用 pkg-config 探测 ncursesw）+ extra_ldflags
`-L{ncurses_libdir}` 双保险（aspell 已验证模式）。OHOS 系统无 ncurses
头文件/pc 文件，探测只会命中 conan 包。

## 上游测试统计（make check，8 程序）

```
PASS: library/tests/test_escape
PASS: library/tests/test_pids
PASS: library/tests/test_uptime
PASS: library/tests/test_sysinfo
FAIL: library/tests/test_version
PASS: library/tests/test_namespace
PASS: src/tests/test_fileutils
PASS: src/tests/test_strtod_nol
# TOTAL: 8   # PASS: 7   # FAIL: 1   # SKIP: 0   # ERROR: 0
```

**test_version 失败定性（环境性，禁改断言）**：`procps_linux_version()`
子用例失败——OHOS `/proc/sys/kernel/osrelease` 为 `"HongMeng Kernel
1.12.0"`（非标准 a.b.c 串）、`/proc/version` 不可读（cat 返回
Permission denied），库内 sscanf 解析失败。
同程序 `LINUX_VERSION` macro 子用例 PASS。前任探索构建、conan create
G2 干净构建与 W3 本地 CI 三次统计完全一致：**7 PASS / 1 FAIL / 0 SKIP**，
该 FAIL 属 OHOS 环境限制，非适配缺陷，未修改上游断言。

另记录：`/usr/include/linux/capability.h` 缺失产生编译警告（guard 宏保护
的 capability 相关代码），不影响编译与测试结果。

## 验证结果

### conan-verify 门禁（G0-G4）：PASS（含警告披露）

G0 知识预扫描命中 E490（autotools 脚本可执行位风险提示，非阻塞——conan
get 保留 tarball 权限位，本机两次构建与 W3 干净构建均未触发）；G1 配方
完整；G2 conan create 干净构建（ci profile）PASS；G3 系统同名库隔离
PASS；G4 产物完整（附警告：无法找到程序包 ID，不影响产物完整性判定）。
verify 侧 L2/L4/L5 因无 cache 路径跳过——实际 L 门禁由 W3 本地 CI 执行。
报告：reports/conan-verify-report.md。

### W3 本地 CI L 门禁（reports/w3-local-ci.log 1105-1140 行）

L0/L1/L2/L5 pass、L1e 破坏性负测试 pass；**L4=warn**（0003-config.guess.patch
内 NetBSD 注释英文单词 targets 命中扫描器危险函数模式 gets\b（无前置锚定
的子串误匹配；补丁实际不含危险调用）——warn 非 fail，abook/aspell 的
config.guess 同类补丁同性质）；18 个二进制 --version 冒烟
全过（free/hugetop/kill/pgrep/pidof/pidwait/pkill/pmap/ps/pwdx/slabtop/
sysctl/tload/top/uptime/vmstat/w/watch）。

### test_package 实测（三次运行，断言语义一致全过）

完整证据链在 reports/w3-local-ci.log（test_procps 输出 1089-1092 行）：

```
procps_uptime: up=1573638.6s idle=26872690.6s
procps_loadavg: 20.78 20.54 20.48
pids API: 52 PIDs fetched via PIDS_ID_PID
libproc2 C API: all checks passed
```

reports/conan-create.log（136-138 行，最终缓存命中复核运行）实测
up=1573470.6s idle=26870340.2s、loadavg 20.85/20.61/20.36、61 PIDs。
uptime 与 PID 计数为系统实时状态，各次运行数值自然不同；断言语义
（rc==0 ∧ up>0 ∧ idle>0 ∧ PID 计数>0）三次运行全部通过。

二进制输出断言（can_run=True，conanrun 环境执行打包产物）：
`ps --version` 含 "procps-ng" ✓、`free` 含 "Mem" ✓、`uptime` 含
"load average" ✓。

## 交付物

| 类别 | 内容 |
|------|------|
| 库 | lib/libproc2.a（-lproc2，pkg_config_name=libproc2） |
| 头文件 | include/libproc2/*.h ×8（diskstats/meminfo/misc/pids/slabinfo/stat/vmstat/xtra-procps-debug） |
| 工具 | 17 bin（free/hugetop/kill/pgrep/pidof/pidwait/pkill/pmap/ps/pwdx/slabtop/tload/top/uptime/vmstat/w/watch）+ sysctl（staging 在 sbin/，conan 包内统一 bin/） |
| 配方 | conanfile.py + conandata.yml + patches/×6 + test_package/（test_procps.c C API 实测 + 二进制断言） |
| 报告 | reports/conan-verify-report.md + reports/conan-create.log + reports/test-report.md |
| 软件级 | ../README.md + ../manifest.yaml + ../commands.json |

## 注意事项

- OHOS 强制静态（R26/R4）：系统 shell（zsh）依赖系统 libncursesw.so.6，
  共享版 top/watch 会引发 RPATH 冲突。
- make 全程 -j1（HMDFS FIFO 限制）。
- 消费者 API 速查：`procps_uptime(double*,double*)`、
  `procps_loadavg(double*,double*,double*)`、`procps_pids_new/unref` +
  `PIDS_VAL(idx,s_int,stack)`（成功调用返回 0，语义与上游 testsuite 一致）。
---

**编译结束**: 2026-09-04 17:39
**最终状态**: built
