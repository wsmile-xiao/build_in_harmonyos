# libee 0.4.1 适配笔记

> 上游：http://www.libee.org（libee-0.4.1.tar.gz，sha256 见 conandata.yml）。
> 同生态已合入配方 libestr 0.1.11（同作者、同年代 autotools 方案）为本配方模板来源。

## 编译环境

- 构建系统：autotools（官方包自带 2012 年 configure，需 autoreconf -fiv bootstrap）
- 编译器：clang/clang++（HarmonyOS aarch64 环境，待真机预检确认）
- 状态：built（待真机 rule4 门禁通过后由 HMBS 提交）

## 编译步骤

1. `get` 解包官方源码；
2. `autoreconf -fiv`（tool_requires automake/1.18 + libtool/2.5.4，OHOS-aware config.guess/sub）；
3. 全量替换生成 configure 中的 `umask 077`→`umask 022`（E011 HMDFS 临时目录不可写），并以 `umask 022 &&` 运行 configure；
4. `configure`（静态默认；OHOS 下显式 `--build/--host` triplets；PkgConfigDeps 提供 libestr）；
5. `make -j1`，随后 `make check -j1` 构建 genfile + ezapi1；
6. 用 `msg/hello hmbs` fixture 实跑 ezapi1，断言退出码 0 且输出含非空 `Formatted event:`；
7. `make install`，落盘 `res/hmbs_upstream.json` 供 test_package 复发标记。

## 上游测试盘点

- tests/Makefile.am 的 TESTS 为空（TESTRUNS 空，tagbucket.sh 已注释），`make check` 本身只构建不执行；
- 两个 check_PROGRAMS：genfile（fixture 数字生成器，main 恒返回 1，非断言测试）、ezapi1（真实事件格式化测试程序）；
- 口径：check 程序数 2（autotools_tests），配方构建验证 + ezapi1 fixture 实跑双重取证，目标 2/2；
- test_package 另有 6 个消费者断言（version/ctx/event/field/format/json 全链路）。

## 依赖版本

- libestr/0.1.11（制品仓 manifest 状态 published，见 archives/l/libestr/manifest.yaml）
- automake/1.18、libtool/2.5.4、pkgconf/3.0.5（tool_requires；前两者制品仓已有，pkgconf 供 PKG_CHECK_MODULES 找 libestr，xmlsec 1.3.12 同型先例）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 官方 https 无法下载（526） | libee.org 仅支持 HTTP | conandata 采用官方 http URL（已有多个合入配方用官方 http 源先例），sha256 与官网 md5 交叉验证一致 |
| 2 | 2012 config.sub 不识别 OHOS triplet | 年代久远 | autoreconf -fiv，用 tool_requires automake 的 OHOS-aware guess/sub（同 libestr 方案） |
| 3 | 上游 TESTS 为空，`make check` 无执行证据 | 上游历史实现 | 配方额外用 fixture 实跑 ezapi1 并做非空内容断言，计数口径写入 MANIFEST 审计 |
| 4 | 真机 `autoreconf: inaccessible or not found`（2026-09-21 预检 compile 失败） | 配方只声明 automake+libtool，缺提供 autoreconf 二进制的 autoconf/2.72，且未生成 VirtualBuildEnv 导致 tool_requires 的 bin/ 未进 PATH，真机最小环境无系统 autoreconf 兜底 | 补 `tool_requires("autoconf/2.72")` + `generate()` 内 `VirtualBuildEnv(self).generate()`（zzuf 0.15 同型先例）；manifest.yaml 同步三件套 |
| 5 | 真机 `bin/aclocal: .aclocal-real: No such file` exit 126（2026-09-23 预检 compile 失败） | 远端 automake/1.18 二进制包半残（DRAFT-6051：打包/传输丢 bin 点文件，conan 不校验缺项仍缓存命中），任何 autoreconf 调用必败，与配方无关 | 配方侧兜底：build 前从 automake share 直拷 config.guess/sub（share 未丢）+ 幂等 E007 OHOS 补丁；autoreconf 仅 try，命中 `.aclocal-real`/126 即警告跳过，用自带 configure + 已刷新脚本继续（libnxml E007 同式） |
| 6 | 上一兜底仍以 `Error 126 while executing` 失败（同日复检 compile 失败，conanfile.py:214） | 上一方案根因假设正确但实现路线错误：`except` 内仅当消息含 `.aclocal-real` 或 `exit status: 126` 才降级，而真机 Conan 实际消息是裸 `Error 126 while executing`，条件永假直接 re-raise，fallback 从未执行 | 换路线：调用前主动探测（新增 `_autoreconf_usable` 读 `which aclocal` 包装头，引用 `.aclocal-real` 但同目录缺文件即判定不可用，直接跳过 autoreconf）；残余失败走无条件 broad-catch 降级，不再匹配异常文本；guess/sub 拷贝后 best-effort 补 copymode（HMBS chmod=0 下不硬要求） |
| 7 | 真机 `configure: /data/service/hnp/bin/bash: inaccessible or not found` 后 `C compiler cannot create executables` Error 77（2026-09-23 预检 compile 失败，conanfile.py:298；上一轮 aclocal/126 已消失，推进到 configure 新失败域，非重复） | profile `[buildenv]` 注入 `CONFIG_SHELL=/data/service/hnp/bin/bash`，该 bash 在 conan 构建目录（HMDFS）内不可用；autoconf 优先用 CONFIG_SHELL 跑 guess/sub/status 并烤进 Makefile SHELL，shell 损坏连带 conftest 环节错乱致编译检查失败（DRAFT-6487、cvsgraph getcwd 探针同族） | 双层 pin 到 hmbs 注入的 `/bin/sh`：`generate()` 内 `Environment().define(CONFIG_SHELL/SHELL)` 存 `hmbs_config_shell` 脚本（配方环境覆盖 profile 值），`build()` 内再写 `os.environ` 兜底，保证 autoreconf/configure/make 所有子进程继承；不重建探测，复用 hmbs 能力 |
| 9 | 本轮 `C compiler cannot create executables` Error 77 复现，但 config.log 首错变为 `/data/service/hnp/bin/clang: inaccessible or not found` exit 127（`--version` 探测即失败，conftest 未执行；TMPDIR/SHELL 均已排除） | 前两轮修了 SHELL/TMPDIR 后仍信任 profile 的 `tools.build:compiler_executables` 绝对路径；该路径在本预检沙箱内不可执行，AutotoolsToolchain 烤进的 CC 直接导致首个编译测试失败（cronolog/kyoto-tycoon 同型已证） | 新增 `_probe_executable`（真机实跑 `--version`）+ `_resolve_compiler`（工具链优先，仅不可执行才回退 PATH 的 clang/cc/gcc）；configure 改走 `CC="..." CXX="..." sh configure --prefix/--build/--host` 内联前缀（shadow 掉 conanbuild.sh 的坏 CC，保留 CFLAGS/LDFLAGS），test_package 同式解析 CC；无猜测，不跳过任何测试 |
| 8 | 同上 `C compiler cannot create executables` Error 77 复现（2026-09-23 预检 compile 失败，conanfile.py:319；hnp-bash 行已消失，shell pin 疑似生效，编译器检查仍不过——同一指纹第 3 次，必须换策略） | 前两轮都是“猜根因直接修”：均无 config.log 实证（预检/CI 摘要从不含 config.log，首个真实错误被汇总行掩盖，coinor-vol 已证）。候选只剩两类：clang 临时文件根（TMPDIR 不可写→首个编译测试即死）或 2012 configure 与工具链的真实-CFLAGS/链接不兼容，摘要日志无法区分 | 换“取证优先”路线：① `autotools.configure()` 包 try/except，失败即 `_dump_config_log()` 把 failed-program 段落+错误行+尾部打成 WARN 行再 re-raise（kyoto-tycoon/myman 同式），下轮按事实定位；② `_ensure_writable_tmp()` 真实写入探测复用 hmbs 注入 TMPDIR，仅不可写才回退 build 内 hmbs-tmp（coinor-vol 真实 open 探针 + rtrlib 候选序），健康时是纯诊断零行为变化 |

## 源码修改

无补丁（R6）。

## 验证结果

待真机预检回填（本轮仅完成未提交工作树，不猜测数字）。

## 注意事项

- 构建产物含 `sbin/libee-convert`，软件级已声明 commands.json（R38）。
| 10 | 真机 `checking for pkg-config... no` 后 `configure: error: The pkg-config script could not be found` Error 1（2026-09-23 预检 compile 失败；上一轮编译器探测已生效，harmonybrew clang 编译 conftest 全部通过，新失败域） | PkgConfigDeps 只生成 .pc 文件不提供二进制，真机最小环境无系统 pkg-config，configure 的 PKG_CHECK_MODULES(LIBESTR) 找不到解析器（xmlsec 1.3.12 同型已证） | 新增 `tool_requires("pkgconf/3.0.5")`，经已有 VirtualBuildEnv 进 PATH，手工 configure 沿用 `env="conanbuild"` 自动带入；manifest.yaml 同步；不改测试口径 |
| 11 | 同指纹第 3 次：`checking for pkg-config... no` 仍复现（2026-09-23 预检；pkgconf/3.0.5 配方已下载但 configure 依然找不到，上一轮“仅加 tool_requires”被证伪） | 在仓 pkgconf 只提供 `pkgconf` 二进制、无 `pkg-config` 别名且无 PKG_CONFIG 转发（xmlsec 1.3.12 第二轮同因已证） | 换显式桥接策略：`_resolve_pkg_config` 按 PKG_CONFIG env/tool 包 bindir/PATH/HNP 预装路径做 `--version` 可运行校验，`_ensure_pkg_config_shims` 落盘 `pkg-config` + 主机前缀 shim（os.open 0o755 免 chmod）并导出 PKG_CONFIG；generate 经 buildenv、build 经内联 `PKG_CONFIG=` 双路注入；无可用时直接抛错 |
| 12 | 本轮 `./config.status[974]: can't create ./conf13885-25291/subs1.awk: Permission denied` → `config.status: error: could not setup config files machinery`（2026-09-23 预检 compile 失败；pkg-config/compiler 均已通过，新失败域） | E011：autoconf 的 `umask 077 && mktemp -d ./confXXXXXX` + `(umask 077 && mkdir)` 在 HMDFS 上建出当前进程不可写的 0700/setgid 临时目录；旧 `sed 's/umask 077 && mktemp/umask 000 && mktemp/'` 只覆盖 mktemp 分支，mkdir 回退仍是 077，且 shell 进程 umask 无法覆盖脚本内显式 umask（E011.kv + zzuf/kyoto-tycoon/kytea 同式已证） | 全量 Python 替换 `umask 077`→`umask 022`（autoreconf 之后执行，使生成 config.status 继承修复，覆盖 mktemp+mkdir 双分支，不依赖真机 sed）；手工 configure 命令前加 `umask 022 &&`（zzuf 先例）；不碰测试口径，不新增环境探测 |
| 13 | 本轮 `CCLD libee-convert` 环节 `ld.lld: error: unable to find library -llibestr`（2026-09-23 预检 compile 失败；configure 已通过，新失败域，make 链接期） | 已合入 libestr/0.1.11 配方 `package_info` 声明 `libs=["libestr"]`（应为 `["estr"]`：产物 libestr.so 链接旗应为 `-lestr`），本配方 `PkgConfigDeps` 按此生成 `Libs: -llibestr`，configure 的 `PKG_CHECK_MODULES(LIBESTR)` 透传该错误旗致链接找 `liblibestr.so`；本配方 `test_package` 手工 `-lestr` 与 libestr 自带 `.pc` 均为 `-lestr`，旁证 | 本配方内修正不碰已发布包：新增 `_libestr_flags()` 从真实依赖包路径组装 `-I<inc>` / `-L<libdir> -lestr`；`generate()` 经 `hmbs_libestr_fix` 脚本预置 `LIBESTR_CFLAGS/LIBS`（`PKG_CHECK_MODULES` 遇预置直接跳过 pkg-config），`build()` 再写 `os.environ` 并拼入手工 configure 的 `env_prefix` 双路注入；保留 `PkgConfigDeps`/测试口径不变 |
| 14 | 本轮 `CCLD libee-convert` 环节 `ld.lld: error: undefined symbol: rpl_malloc`（event.c/value.c/tagbucket.c 等 14 处引用，2026-09-23 预检 compile 失败；上一轮 `-llibestr` 已消失，configure 通过后 make 链接期新失败域） | 经典 `AC_FUNC_MALLOC` 交叉编译误判：`--host=ohos` 下 configure 无法运行 `malloc(0)` 测试，默认 `ac_cv_func_malloc_0_nonnull=no`，给全树加 `-Dmalloc=rpl_malloc` 却从不编译替代实现，致静态归档内所有 `malloc` 调用悬空；与编译器/TMPDIR/shell 无关（conftest 全过，倒在最终可执行链接） | 跨编译标准预置：`generate()` 经 `hmbs_libestr_fix` 脚本导出 `ac_cv_func_malloc_0_nonnull/realloc=yes`，`build()` 再写 `os.environ` 并拼入手工 configure 的 `env_prefix` 双路注入；不断言 OHOS 源码行为，仅复用 autoconf 缓存变量语义，不碰测试口径 |
| 15 | test check building ezapi1.c reports libestr.h not found (2026-09-23 preflight compile fail; src built, tests failed) | LIBESTR_CFLAGS preset did not land in tests/Makefile (per-target CPPFLAGS miss); toolchain global CPPFLAGS channel also empty for that unit | keep LIBESTR preset, add global CPPFLAGS/CFLAGS -I and LDFLAGS -L fallback via Environment.append + os.environ + manual configure env_prefix; no test change |
| 16 | make install fails install-eeincHEADERS Error 64 with doubled dest <pkg>/storage/.../<pkg>/include (2026-09-23 preflight package fail; upstream 2/2 already passed) | manual configure used --prefix=package_folder while Autotools.install() auto-prepends DESTDIR=package_folder, so DESTDIR+prefix doubles | change manual configure to --prefix=/ matching AutotoolsToolchain default, keep autotools.install() DESTDIR flow; no test change |
| 17 | make install install-eeincHEADERS Error 64 persists with dest <pkg>//include/libee after prefix=/ fix (2026-09-23 preflight package fail; upstream 2/2 passed) | prefix=/ expands to //include double-slash which preflight install shim rejects; single strategy change from prefix-only | pin --includedir/--libdir/--bindir/--sbindir to single-slash absolutes + package() retry with INSTALL_DATA/PROGRAM/SCRIPT=cp -p fallback; no test change |
| 18 | test_package `CHECK-FAIL: rfc5424-format` exit 1（2026-09-23 预检 evidence 失败；上游 2/2 已通过，消费者 6 断言中 5 过、格式化断言挂） | 上游 `src/syslog_enc.c: ee_fmtEventToRFC5424` 初始化 `r = -1`，成功路径仅 tags 分支经 CHKR 更新 r，无 tag 事件恒返回 -1 但 *out 正常填充；上游 tests/ezapi1.c 从不检查返回值（直接打印），本测试却要求 `rc == 0`，属测试对上游 bug 的误断言，非库功能故障 | 测试改为与上游一致用法：忽略返回值，断言 `out != NULL` 且内容非空并含 `msg=`/`hello hmbs` 负载（防 toybox 式空输出假通过）；断言数仍为 6，配方与 MANIFEST 口径不变 |
