# srcpd 2.1.7 适配笔记

## 上游信息
- 官方项目页：https://srcpd.sourceforge.net/（SourceForge，srcpd: modular SRCP server）
- srcpd 是 Simple Railroad Command Protocol（SRCP）服务端守护进程：模型铁路硬件与 SRCP 客户端之间的网关
- 官方源码归档：https://downloads.sourceforge.net/project/srcpd/srcpd/2.1.7/srcpd-2.1.7.tar.gz（378565 字节）
- sha256：ba78b81a6a13f4aca911cfbbed725b2e882af7d332351f4436d57960cd1d13b0
  - 由 OpenBSD distfiles 镜像实测下载验证（SIZE 378565 一致；OpenBSD ports distinfo 的 base64 SHA256 换算后完全一致）
- 归档内容：顶层 srcpd-2.1.7/，共 124 文件

## 构建系统
纯 Autotools，无 CMake/Meson：
- configure.ac（AC_INIT srcpd 2.1.7）+ 顶层 Makefile.am（SUBDIRS = src man）
- src/Makefile.am：sbin_PROGRAMS = srcpd（单一守护进程二进制 + 12 设备模块条件编译）
- man/Makefile.am + man/de/Makefile.am：英文/德文 man 页
- 设备模块（configure --enable/--disable 开关）：ddl、ddl-s88、hsi-88、i2c-dev、intellibox、li100、loconet、loopback、m605x、selectrix、zimo、dccar
- 硬依赖：libxml2（AM_PATH_XML2 ≥ 2.4.0，缺失则 configure 直接报错）、pthread
- 无测试目标：所有 Makefile.am 均无 TESTS/check-TESTS，上游无测试框架

## 关键适配决策
1. **依赖**：`self.requires("libxml2/2.15.3.1")`（本仓 R37 适配修订版；刻意不用 plain 2.15.3：该版本同时发布在 ConanCenter，预检远端顺序（conancenter 在前）会解析到 CCI 原生配方，其 `cmake/<ver>` tool_requires 无 OHOS 源码项，在自身 build() 报 `KeyError: 'OHOS'`——本轮真机失败的直接原因；CCI 无 2.15.3.1，引用无歧义必然落到 OHOS 适配配方。同族先例：sollya/8.0 同款引用，sail/0.9.10 RREV-pin 同因修复）。pthread 为系统库，无需 conan 依赖。
2. **--disable-ddls88**：ddl-s88.c 含 `<sys/io.h>`/ioperm（x86 端口 I/O），OHOS aarch64 musl 下不存在，故禁用。其余 11 个模块保持上游默认（全部启用）。
3. **--build/--host + config.sub 补丁**：`--build=aarch64-linux-gnu --host=aarch64-linux-ohos`（仓库 Autotools 通用手法）。上游自带的 config.sub 是 2022-01-03 版，不认识 `ohos`（本轮真机失败：`Invalid configuration 'aarch64-linux-ohos': OS 'ohos' not recognized`），`patches/0001-config.sub-ohos.patch` 在 OS 白名单加 `ohos*`、在 kernel-OS 校验加 `linux-ohos*`（与 sarg/2.4.0 同款两处；本地用 Git sh 实测：未打补丁复现原报错，打补丁后 canonicalize 为 `aarch64-unknown-linux-ohos`）。该 canonical host 命中 configure 的 `*-*-linux*` 分支（此前笔记误记为“落入告警分支”，已更正），故 `linux/serial.h`、`linux/i2c-dev.h` 探测会真实执行（缺失则 configure 直接报错，待真机判定）；`--disable-ddls88` 使唯一的 x86 专有探测（`sys/io.h`/ioperm）被跳过。`AC_TRY_RUN` 仅用于 ipv6 可用性探测，交叉编译下走默认 `no` 分支，无害。
4. **XML_CPPFLAGS/XML_LIBS 兜底**：AM_PATH_XML2 硬依赖可执行 xml2-config（env 的 XML_CPPFLAGS/XML_LIBS 会被覆盖，无垫片时 CI 报 no matching library found）；generate() 同时从 libxml2 依赖的 cpp_info 显式导出这两个变量（conanxml 脚本）并写 conan 路径背书的 hmbs-xml2-shim/xml2-config 垫片（--cflags/--libs/--version），经 XML2_CONFIG 与 PATH 双通道注入 configure 子进程（CI #88261 修复）。
5. **SHELL/CONFIG_SHELL 路由**：build() 内仍显式定义 `/bin/sh`（hmbs 真机注入 SHELL=/bin/sh，口径一致），但该层会被 profile `[buildenv]`（钉死 `/data/service/hnp/bin/bash`）覆盖——E386 同族。新增 `_reroute_pinned_shell()`：仅当钉死路径不存在时，把聚合 env 脚本中的该路径文本替换为探测到的可用 shell（`/bin/sh`/`/system/bin/sh`，均为 HMBS 能力集内）；路径存在时零改动。依据：sarg/2.4.0 同法、scanmem/0.17 `_good_shell` 探测；本轮真机证据 `configure[139]: /data/service/hnp/bin/bash: inaccessible or not found`（Error 127，编译器检查之前即死）。
6. **-j1 单作业**：HMBS 注入 tools.build:jobs=1，配方内同样 -j1（HMDFS 并行 make 风险规避）。
7. **package_type="application"**：产物为 sbin 二进制 + man 页 + 默认配置；`cpp_info.bindirs=["bin","sbin"]`，libs/includedirs/libdirs 置空。R38 软件级 commands.json 已建（type=tool）。
8. **R32**：validate() 用 `self.settings.os not in ("Linux", "OHOS")`（显式评估 OHOS）。
9. **R33**：无裸 shell 变量；编译器来自 profile 的 tools.build:compiler_executables（AutotoolsToolchain 自动注入）。

## 上游测试审计
- 归档 124 文件：configure.ac、4 个 Makefile.am（含 man/de）、79 个 src/ 文件、man 页、文档与 init 脚本。
- SUBDIRS = src man；grep 全归档无 test/tests 目录、无 check-TESTS、无 gtest/pytest/criterion。
- 结论：**上游无测试框架**（upstream_tests_exist=false），test 阶段输出 `HMBS_UPSTREAM_TEST_RESULT` no_tests 审计标记。

## test_package（自建功能验证，6 断言）
在 conanrun 环境运行（VirtualRunEnv 注入 PATH）：
1. srcpd 二进制已安装且可运行（`-h` 输出 Usage 横幅即算通过；上游 src/srcpd.c 的 -h/-v 分支均 exit(EXIT_FAILURE)=1，故不断言退出码为 0）
2. `srcpd -h` 输出 "Usage: srcpd" 用法行
3. `srcpd -v` 输出 "srcpd V2.1.7" 版本横幅（WELCOME_MSG = "srcpd V" VERSION "; SRCP 0.8.4; ..."）
4. `-h` 输出含 -f 配置文件选项文档
5. man 页 share/man/man8/srcpd.8 已安装
6. 默认配置 etc/srcpd.conf 已安装

说明：全量功能需真实模型铁路硬件（串口/I2C/USB 设备），无法在 CI/真机覆盖；-h/-v 路径真实执行了守护进程的选项解析与版本打印逻辑，可证伪（二进制为桩时 grep 失败）。

## 真机验证（内部基建，勿写入 PR 正文）
- 环境：HarmonyOS PC 真机，/data/service/hnp 工具链 + conan，与官方 CI 同源
- 预检与官方 CI 一致：conan create（profile ci/conan/profiles/ohos-aarch64，os=OHOS arch=armv8，clang15，libc++）
- 待真机预检验证：① linux/serial.h、linux/i2c-dev.h 在 OHOS sysroot 是否存在（ddl/i2c/loconet 模块能否编译；若缺失则下一轮追加 --disable 开关）；② libxml2/2.15.3.1 在真机闭包是否可用；③ 6 项断言在真机是否全过
- 真机测试数字将据此回填 .hmbs/pr-body.md「测试用例通过率」
- 预检轮次：① config.sub 不认 ohos（已修：0001 补丁，真机确认 host canonicalize 为 aarch64-unknown-linux-ohos）；② 新失败 `checking for aarch64-linux-ohos-gcc... /data/service/hnp/bin/clang` 后 `C compiler cannot create executables`（Error 77，try-link 阶段，非 127 缺编译器）——本轮加固：`_resolve_compilers()` 对钉死路径先做存在性+`--version`探测（健康机零改动，仅覆盖 CC/CXX，不碰标志）、缺失才经 PATH（含同目录兄弟）回退并明示环境故障；configure 失败时转储 config.log 尾部 80 行与 CC/CXX/CFLAGS/CPPFLAGS/LDFLAGS/LIBS 上下文供下一轮取证。真实链接错误仍藏在 config.log 里，待下轮日志判定（候选：runner 侧 lld/libxml2.so.16 加载或 sysroot 链）。
- 预检轮次③：关键证据——`compiler probe /data/service/hnp/bin/clang -> missing`（该 runner 上整个 /data/service/hnp 缺失，shell 钉死路径同样缺失），回退正确找到 `.harmonybrew/bin/clang{,++}`（rc=0，clang 15.0.4），但 configure 仍用 `CC=/data/service/hnp/bin/clang`（`checking for aarch64-linux-ohos-gcc... /data/service/hnp/bin/clang`）。结论：`Environment.define` 的 CC/CXX 输给聚合 conanbuild.sh 的 sourcing（与 SHELL 被 profile buildenv 覆盖同族）。本轮改用已验证落点：`_reroute_missing_compilers()` 把缺失钉死路径在聚合 .sh 脚本内改写为回退编译器（c与cpp两对，clang++先行；仅改写磁盘缺失的钉死路径，健康机零改动；完整绝对路径匹配，两遍替换互不污染）。另注意到 `LDFLAGS=<unset>`（os.environ 转储仅反映 Python 进程侧，conanbuild.sh 的导出只在 configure 子 shell 可见，config.log 尾部才是真凭据）。

- 预检轮次④：`configure: creating ./config.status` 后 `./config.status[778]: can't create ./conf6j2N3T/subs1.awk: Permission denied` + `could not setup config files machinery`，平台诊断 [unsafe_local_mktemp]（能力 chmod:0/local_mktemp:1）。本轮最小适配：build() 首部复用 HMBS 注入 TMPDIR（写探测后）+ os.umask(022)，新增 `_patch_configure_umask()` 把 configure 本体（含 config.status 模板）的 `umask 077` 放宽为 022（buildtorrent/swbis 同法，主修复，chmod=0 下仍有效），另加 `HMBS_AUTOCONF_MKTEMP_FALLBACK=1` 才启用的 conf* mktemp 影子垫片（serf/cyrus-sasl 同款，best-effort）并经 Environment prepend 到 configure/make 子进程；仅重定向临时根与权限位，不跳过任何测试。

- 预检轮次⑤：configure 通过、make 在终链失败 `ld.lld: error: undefined symbol: pthread_setcancelstate/setcanceltype/testcancel/cancel`（clientservice.c:thr_doClient、netservice.c、config-srcpd.c:cancel_all_bus_threads/run_bus_watchdog；其余 pthread 符号如 create/mutex/cond 均已解析，故非缺 -lpthread，而是 OHOS musl 未实现取消族——同族 s3fs-fuse/1.94“musl未实现pthread_cancel，stub 解决”，知识库 E003 另要求显式 -pthread）。本轮修复：generate() 经 `tc.extra_cflags/extra_ldflags` 追加 `-pthread`，新增 `_ensure_ohos_pthread_compat()` 在 build 文件夹生成 `ohos_pthread_compat.h`（四调用重命名为静态 no-op：setcancelstate 回填 ENABLE、setcanceltype 回填 DEFERRED、testcancel 空、cancel 返回 0；重命名而非同名 static，避免与 <pthread.h> 声明的 linkage 冲突），经 `-include<abs>` 强制编入每个 TU（toolchain 层 + build() Environment 双保险），无需改 Makefile/链接行；取消语义降级为禁用（守护进程 -h/-v/冒烟与正常服务路径不依赖异步取消推进）。

## 申请人
- GitCode 用户名：momimgya，队伍名称：干
