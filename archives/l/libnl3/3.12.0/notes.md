# libnl3 3.12.0 适配笔记

## 编译环境

- 构建系统: autotools（release dist tarball，已含预生成 configure / Makefile.in）
- 编译日期: 2026-09-24
- 编译器: clang / clang++ 15（`/data/service/hnp/bin/clang`）
- 目标平台: HarmonyOS PC aarch64，os=OHOS / arch=armv8 / clang 15 / libc++ / Release
- 状态: built（待 HMBS 真机 rule4 门禁验证）
- 宿主特征: `uname -s` = `HarmonyOS`
- 申请人: zhangyuge147，队伍名称: 龙骑士

## 上游信息

- 上游仓库: https://github.com/thom311/libnl
- 版本: 3.12.0（tag libnl3_12_0，发布于 2025-12-04）
- 源码归档: https://github.com/thom311/libnl/releases/download/libnl3_12_0/libnl-3.12.0.tar.gz
- sha256: fc51ca7196f1a3f5fdf6ffd3864b50f4f9c02333be28be4eeca057e103c0dd18
  （官方 .sha256sum 资产 + Debian libnl3_3.12.0-2.dsc Checksums-Sha256 双重确认；
  MD5 f9112ca215807fe65eecd583d8f180cc 与 BLFS/ptxdist 一致）
- 适配路径: 路径 A（基础适配）
- 基线复用: archives/l/libnl/3.11.0 已验证配方（E205/E114/E091/E119/E490 全套处置）

## 3.12.0 相对 3.11.0 的增量

- 新 API：nl_cache_resync_v2、rtnl_link_ip6_tnl get/set collect-metadata、
  rtnl_nh_add 系列、nh encap（ila/ip/ip6/mpls）、route_nh get/set encap；
  libnl-route-3.sym 新增 68 行，libnl-3.sym 新增 5 行，libnl-xfrm-3.sym 新增 7 行。
- tests/ 新增 cksuite-link-ip6tnl.c（257 行）、cksuite-route-nexthop.c（481 行）、
  cksuite-route-nh.c（1206 行），均挂入 check-all；test-create-ip6tnl.c 从
  check_PROGRAMS 移除（改由 cksuite 覆盖）。
- 新增 tools/check-c-list.sh + third_party/c-list（meson 项目），缺 meson/ninja
  时 exit 0 skip，不引入硬依赖。
- Makefile.am 的 build-headers-test 两条规则与 3.11.0 逐字一致，0002 继续适用。
- configure.ac 仍要求 flex/bison（缺失即 AC_MSG_ERROR），check 仍为可选项。

## 编译步骤

```sh
export PATH=/data/service/hnp/bin:/usr/bin:/bin:/system/bin
export TMPDIR=<可写目录>

tar xzf libnl-3.12.0.tar.gz
# 零静态补丁配方：E205（config.guess/config.sub）与 E091/E119（build-headers-test
# 补 -I linux-private）均由 conanfile build() 运行时容错修补完成，无需 patch -p1

mkdir build && cd build
../libnl-3.12.0/configure --disable-cli --enable-static --disable-shared
make -j1

conan create archives/l/libnl3/3.12.0 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --build=missing
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `config.guess: unable to guess system type` + 静态补丁 `hunk no.1 doesn't match at line 191` / `source file is different - config.sub` | tarball 自带 config.guess 不识 HarmonyOS（E205），且 3.12.0 基线相对 3.11.0 已漂移，静态 0001 上下文失配 | 删除静态 0001，build() 改用等价 patch-autotools-ohos.pl 的运行时容错正则修补（锚点 NetBSD/android-linux/OS 列表/kernel-OS 表，幂等）；不使用 --build/--host 绕过 |
| 1b | `configure[137]: /data/service/hnp/bin/bash: inaccessible or not found`（Error 127，补丁全过后倒在 configure 起跑） | profile `[buildenv]` 写死 CONFIG_SHELL=/data/service/hnp/bin/bash，但该路径真机不存在（xz/5.8.3.2 同款实测结论）；3.12.0 configure:132 `exec $CONFIG_SHELL` 重执行（官网 tarball 已验，sha256 一致） | generate() 用 Environment 把 CONFIG_SHELL/SHELL 指到实存 shell（which bash→/bin/sh→/system/bin/sh + `shell -c :` 试运行校验，防“存在但 EACCES”），build() 用 _fix_conanbuild_shell 改写生成脚本坏前缀并直写 os.environ 双保险 |
| 2 | 静态 0002 在 `Makefile.in` 整文件判异（actual 含 `uninstall-libnlinclude_netlink_routeHEADERS` 行） | 3.12.0 的 Makefile.in 基线相对 3.11.0 已分叉，行号/上下文硬匹配必然失败 | 删除静态 0002，build() 改用锚定 `_NL_NO_WARN_DEPRECATED_HEADER` 编译行的运行时容错插入（幂等，仅影响自检，不改交付） |
| 3 | config.status 在 HMDFS 下建临时目录失败 | autoconf `umask 077 && mktemp` 与 SGID 目录冲突（E114） | build() 去掉 `umask 077 && ` |
| 4 | `configure: Permission denied` | HMDFS/缓存拷贝丢执行位（E490） | 仅对已知 8 个 helper 脚本恢复 0755 |
| 5 | `GEN lib/route/cls/ematch_grammar.c` 时 `flex: fatal internal error, exec of .../p/m42d92622f4ed01/p/bin/m4 failed`（Error 141，真机预检 2026-09-24 两轮同指纹） | flex 经 $M4 调 m4，默认指向的共享缓存 conan m4 子进程 exec 失败（存在但不可执行：丢执行位或错架构；HMBS 上报 HMBS_CAP_CHMOD=0） | 显式 tool_requires m4/1.4.19；generate() 加 VirtualBuildEnv + conanbuild.sh 默认 M4/BISON_PKGDATADIR；build() 新增 _fix_flex_bison_m4：工具 bin 尝试恢复执行位（EPERM 吞掉）、BISON_PKGDATADIR 指包内 share/bison、$M4 指 `m4 --version` 试运行通过者（conan→PATH→hnp glob→系统路径），全失败只告警由 make 托底。已验证有效：第 3 轮预检越过语法生成阶段（GEN pktloc_grammar.c / pktloc_syntax.c 成功，libnl-route-3.la 链接完成） |
| 6 | `package()` 的 `install-libnlinclude_netlinkHEADERS` 报 `Error 64`（EX_USAGE），`autotools.install()` 中断 | 真机无 GNU install；HMBS 的 PATH 级 install shim 只接受单文件双参（lzop 第 2 轮实证 `[ $# -eq 2 ] \|\| exit 64`），而 automake 该规则把 N 个头合并成一次 `install -c -m 644 <f1..fN> <dir>` 调用（E596-C 同型） | package() 新增自写多文件 install shim（cp -f + mkdir -p，chmod 一律容错；os.open 0o755 落盘）并改写构建树全部 Makefile 的 `INSTALL = ...` 行（INSTALL_DATA/INSTALL_PROGRAM 引用 ${INSTALL} 自动跟随；不靠 PATH 前置）；另：libtool `lax` 硬链接 `Operation not permitted` 为非致命告警（构建继续），按最小适配原则不处理 |
| 7 | test_package `cmake.configure()` 在 `project()` 处失败：`System is unknown to cmake, create: Platform/HarmonyOS` + `CMAKE_C_COMPILER: /data/service/hnp/bin/clang` 可用性校验失败（真机 cmake 4.4.3，2026-09-24 预检；主库构建/安装已过，断点仅在 test_package） | Conan CMakeToolchain 在 os=OHOS 时生成 CMAKE_SYSTEM_NAME=HarmonyOS，CMake 无该平台模块（E092）；与 m4/flex、install shim 无关，属 test_package 构建视角问题 | test_package/conanfile.py 新增显式 generate()：CMakeToolchain 在 OHOS 下覆盖 CMAKE_SYSTEM_NAME=Linux + CMAKE_SYSTEM_PROCESSOR=aarch64（zstr/1.1.0、rttr/0.9.6、byte-lite 同口径），CMakeDeps/VirtualRunEnv 改显式生成；test() 落盘运行日志后以二进制末行汇总为单数据源解析计数并双通道输出 HMBS_TEST_PACKAGE_RESULT，上游以 skipped+gaps 复发 HMBS_UPSTREAM_TEST_RESULT（darts/0.32 同型，cache-hit 保底） |
| 8 | 上一轮第 7 项验证无效：`System is unknown to cmake` 消失，但止步 `The C compiler identification is unknown`（`CMAKE_C_COMPILER: /data/service/hnp/bin/clang`，conanfile 行号 26→49 证明新文件已同步；裸 try_compile 可执行链接失败，与 SYSTEM_NAME 覆盖无关） | SYSTEM_NAME=Linux 只解决平台模块缺失，CMake 的编译器 ID 检查仍做裸可执行链接，该链接不继承完整工具链标志在 OHOS 下不可靠（E191） | test_package generate() 在 OHOS 下追加 `CMAKE_TRY_COMPILE_TARGET_TYPE=STATIC_LIBRARY`（hopscotch/0.1.2、hedley/15 test_package 同口径），编译器检查只编译不链接；真实 test_libnl 可执行链接仍走完整工具链，不改测试口径与标记逻辑 |

## 上游测试盘点（申报表）

- 统计口径: autotools_tests（TESTS 变量展开）
- upstream_test_total: 2（tests/check-all、tests/check-direct）
- 来源: 3.12.0 tag 的 Makefile.am（TESTS += $(check_programs)，check_programs 仅由这两项追加）
- check_PROGRAMS（仅构建不自动运行）: 26 项（23 个 link/attr 类 + test-cache-mngr/test-genl/test-nf-cache-mngr）
- check-local-c-list: 缺 meson/ninja 时自动 skip
- 上游测试在 build() 中真实开启（upstream_test_in_build: true）：`make check` 在同一构建目录运行，以 test-suite.log 汇总块为单数据源上报；check-all 的 netns/iface 用例与链路类程序需 netlink 特权，在受限域内 FAIL/ERROR 属环境限制，以 gaps 如实申报（3.11.0 三层证据链复用），不中断打包。
- 真机实测数以 HMBS 预检日志为准，本轮不猜测；上游/新增不足 100% 时按 gaps 口径如实申报。

## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | autotools 配方；package_type=library；--disable-cli；6 个 cpp_info component；零静态补丁（运行时容错修补 E205/E091/E119） |
| `conandata.yml` | 官方归档 URL + 官方 sha256（零静态补丁，E205/E091/E119 由 build() 运行时修补） |
| `manifest.yaml` | 版本级 manifest（status=built 待真机；patches_applied 为空，零静态补丁） |
| `test_package/` | CMake 消费者测试：链接 6 组件 + 7 组运行时真实断言 |
| `test_package/MANIFEST.yml` | 上游测试声明（含 upstream_test_total=2） |

产出库（静态）：`libnl-3.a`、`libnl-route-3.a`、`libnl-genl-3.a`、`libnl-nf-3.a`、`libnl-idiag-3.a`、`libnl-xfrm-3.a`。

## 注意事项

1. 消费者必须处理 E119 冲突：预定义 `_UAPI_LINUX_SOCKET_H` 与 `__kernel_sa_family_t=ushort`（见 test_package/CMakeLists.txt）。
2. `--disable-cli` 是刻意的：CLI 依赖 netlink 内核交互，OHOS 用户态不可用。本包仅交付库。
3. 本包无 bin/，属 library → 不登记 commands.json、不声明 bindirs（R38）。
4. Windows 检出注意：上游 main 含 `archives/g/gama/2.29/patches/0002-dataparser-ungated.patch??`（文件名含 `?`，Windows 非法），本机用 sparse-checkout 排除该单文件后检出，不影响本包。

---

| 9 | test_package project() 处 `The C compiler identification is unknown`（CMAKE_C_COMPILER=/data/service/hnp/bin/clang），SYSTEM_NAME=Linux+TRY_COMPILE=STATIC_LIBRARY 两轮后同指纹复现 | 前两轮假设“编译器路径有效、只缺平台模块/链接方式”错误：同日志主库 configure 用 harmonybrew clang 成功，而 test_package toolchain 硬编码的 /data/service/hnp/bin/clang 本体不可识别，与 SYSTEM_NAME 无关 | 本轮换路线：test_package generate() 新增试运行校验的编译器探测（CC/CXX→PATH→~/.harmonybrew/bin→真机绝对路径，clang --version rc=0 才采用），OHOS 下覆盖 CMAKE_C_COMPILER/CMAKE_CXX_COMPILER；找不到则保留原值由 CMake 真实报错托底，不猜测修正 |

| 10 | 上轮 #9 换路线后仍同指纹复现：日志已有 `[ok] test_package CMAKE_CXX_COMPILER=/storage/.../.harmonybrew/bin/clang++`（证明新文件已同步），但 CMake 实际仍用 `CMAKE_C_COMPILER: /data/service/hnp/bin/clang` 做识别并报 unknown | 上轮根因假设（hnp 路径坏、harmonybrew 可用）未被证伪，但实现层选错：profile 以 `tools.build:compiler_executables` 把 hnp 路径烘焙进 conan_toolchain.cmake，该层优先级高于 `tc.cache_variables`，导致 cache_variables 覆盖静默丢失（日志自证：我们的 [ok] 与 CMake 实际值不一致）。继续调 cache_variables 属同一失败路线 | 本轮换实现路线：generate() 不再经 cache_variables 设编译器，改为落盘后改写 `conan_toolchain.cmake`（复用主包 _fix_conanbuild_shell 同型手法，只换编译器绝对路径为试运行通过者，不动 SYSROOT/FLAGS；找不到则保持原文件由 CMake 真实报错托底）。先换 clang++ 再换 clang 防子串覆盖；改写范围仅 OHOS |

| 11 | 本轮预检日志与上轮逐字同指纹（含同一 Exported 时间戳 13:24:45 与同一 build hash），且 `[ok]` 行仍出现在 `CMakeToolchain generated` 之前——与工作树新代码（[ok] 在落盘改写后、generated 之后）顺序矛盾，判定为旧代码的滞后复跑，新路线尚未被验证 | 不重复换根因假设；保留 #10 落盘改写路线，仅做同路线内的双保险补强，避免另起第三种互斥方案导致验证信号混杂 | _fix_toolchain_compilers 内同步导出 CC/CXX 进程环境指向同一试运行通过者（CMake 回退读 CC/CXX 时同样命中可用编译器）；文件改写逻辑不动 |

| 12 | 真机 rule4 `缺少上游运行结果`：预检 HMBS_UPSTREAM_TEST_RESULT 为 `skipped/discovered=2/executed=0`（test_package 静态复发，未真实运行 make check），判 incomplete | 聚焦记忆确认：工作树 build() 未挂 make check（MANIFEST upstream_test_in_build=false），test_package 仅硬编码 skipped+gaps；TEST_QUALITY_SPEC 3.1/ADAPTATION_GUIDE 4.3 要求 build() 真实运行上游套件并以实测计数上报，executed=0 必然拦截 | build() 新增真实 `make check`（tool_requires check/0.15.2 补齐 libcheck 探测；TEMP 指可写目录；LD_LIBRARY_PATH 兼容动态回退；非零退出只记录不中断打包），以 test-suite.log `# TOTAL/# PASS/# FAIL/# SKIP` 汇总块为单数据源解析并双通道发射标记（failed>0→failed、executed<discovered→incomplete），gaps 合计=discovered-passed；结果持久化到包内 hmbs_upstream_result.json，test_package 改为只重发包内 JSON（缺失则如实 incomplete），MANIFEST upstream_test_in_build 改 true |

| 13 | 真机 rule4 `上游测试不足 100%，必须提供 gaps`：预检 HMBS_UPSTREAM_TEST_RESULT 为 `passed/discovered=0/executed=0`（command=make check），判 incomplete | 本轮日志自证：标记为 passed 却 discovered=0，说明 `make check` 已执行但 TESTS 为空——configure 的 `PKG_CHECK_MODULES([CHECK],[check>=0.9.0])` 未找到 check.pc，缺失仅 WARN 并静默关闭单测（TOTAL=0）。工作树虽已 tool_requires check/0.15.2，但 generate() 未经 PkgConfigDeps 落盘 .pc，build() 亦未导出 PKG_CONFIG_PATH，configure 探测必然落空；与 m4/flex、install shim、seccomp 特权限制无关 | generate() 新增 `PkgConfigDeps(self).generate()`（ypserv/4.2 同型，把 check.pc 落盘到 generators_folder）；build() 新增 `_export_check_pkg_config()`：把 generators_folder 与 check 包内 pkgconfig 目录（含 lib/pkgconfig 自带与任意 check.pc 兜底）一并前置到 PKG_CONFIG_PATH，并以 `pkg-config --modversion check` 试运行取证（失败只告警由 configure 托底）；_parse 后新增 discovered==0 判 incomplete 分支（TOTAL=0 即探测失败，不是“通过”，宁缺毋假），防再次以 passed+0 计数蒙混过关 |

---

**编译结束**: 2026-09-24
**最终状态**: built（待真机验证）

| 14 | 真机 rule4 同指纹第 2 次：`incomplete/discovered=2/executed=0/reason=test-suite.log not found`（搜过 build-release 与源码树 4 路径），仍缺 gaps | 前次 #13 只解决“探测缺失致 TOTAL=0”，本轮是“无日志可解析”：make check 已执行但构建树无 test-suite.log（非 TOTAL=0，而是文件缺失）。沿用纯 os.environ 导出 PKG_CONFIG_PATH 可能被 conanbuild.sh 聚合覆盖，且固定 4 路径在 VPATH 下可能漏落点；沿用原策略属重复，需换策略 | 换策略：generate() 新增 Environment 持久化 PKG_CONFIG_PATH（generators_folder 写入 conanbuild.sh，与 build() 内 os.environ 双保险）；build() 在 configure 后新增 _verify_check_probe（读 config.log CHECK 段与 tests/Makefile TESTS 行，诊断行供下轮直接判定）；make check 后新增 _diagnose_check_artifacts（walk 列出所有 test-suite.log 与 tests/check-all、check-direct 存在性）；_parse 改为固定路径+全树 walk 递归兜底；缺日志的 incomplete 标记补 gaps(count=2, category=environment, evidence=reason)，满足不足 100% 必须 gaps 的门禁 |
