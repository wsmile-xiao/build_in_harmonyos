# bwm 0.6.3 适配笔记

## 编译环境
- 构建系统: autotools（configure.in + Makefile.am）
- 编译日期: 2026-09-09
- 编译器: clang
- 状态: built（待真机预检 evidence 回填后转 published 判定）

## 命名说明
- 本包名 `bwm`，上游为 `vgropp/bwm-ng` 的 `v0.6.3` 标签（Bandwidth Monitor NG）。
- 经检索（GitHub / Debian / OpenWrt / Alpine / Gentoo），不存在独立命名为 `bwm` 且版本为 `0.6.3` 的上游 tarball；`bwm-0.6.3.tar.gz` 的唯一可信来源即 `bwm-ng v0.6.3`（sha256 `c1a552b6ff48ea3e4e10110a7c188861abc4750befc67c6caaba8eb3ecf67f46`，与 OpenWrt/Gentoo/Alpine 一致）。
- 上游二进制历史名称为 `bwm-ng`；本包同时安装 `bin/bwm-ng`（上游原名）与 `bin/bwm`（包名别名，同一静态二进制拷贝），消费者可用任一名称调用。
- 与仓库已合入的 `archives/b/bwm-ng/0.6.3` 同源但包名不同；`bwm/0.6.3` 在制品仓无既有版本，不触发 R37/L0j 同版本冲突。

## 编译步骤

1. 下载上游 tag `v0.6.3` 源码包（sha256 见 conandata.yml）。
2. 将 `configure.in` 复制为 `configure.ac`（autoreconf >= 2.70 不接受 `.in`）。
3. `tool_requires`：m4/1.4.19、autoconf/2.72、automake/1.18、libtool/2.5.4、perl/5.42.2（真机 conanbuild 环境内无 autotools，需完整自举链；autoreconf 以 `env="conanbuild"` 运行，否则 PATH 缺失报 `autoreconf: not found`；perl 供下述 automake shims 使用，与 autoconf/2.72 同版本）。
4. `autoreconf -v -i -f`（执行前：① TMPDIR 可写兜底；② 在 `<build>/.hmos_fix` 生成 `aclocal`/`automake` shims 并前置到 PATH，绕开 automake 包装脚本写死的构建机 perl 路径，否则 OHOS 上报 `126`/`No such file`）。
5. E007：对生成的 `config.guess`/`config.sub` 打 HarmonyOS 识别补丁（不传 `--build`/`--host`）。
6. E114：将生成 `configure` 中的 `umask 077` 改为 `umask 022`。
7. `./configure --prefix=/ --without-curses --without-ncurses --with-proc-netdev`，并加 `-static`。
8. `make`（上游无 TESTS，不调用 `make check`；`upstream_test_in_build: false`，对齐已合入主干的 osmctools/0.9 + sipcalc/1.1.6 范例）。
9. 上游无测试证据由 `test_package/test.sh` 在 test 阶段输出 `HMBS_UPSTREAM_TEST_RESULT(status=no_tests)`（`test_package/conanfile.py` 在包缓存命中时复发，保证每轮必现）。
10. `make install` 打包 `bin/bwm-ng`，并拷贝别名 `bin/bwm`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.guess 无法识别 OHOS | GNU config.guess 无 HarmonyOS 分支（E007） | autoreconf 后补丁 config.guess/sub，禁止 `--build`/`--host`（R15） |
| 2 | autoreconf 找不到 aclocal/automake；真机 `autoreconf: not found` | 真机 conanbuild 环境 PATH 无 autotools，且配方缺 autoconf/m4、run 未激活 conanbuild（E178） | `tool_requires("m4/1.4.19"+"autoconf/2.72"+"automake/1.18"+"libtool/2.5.4")`（libdill/burp2 同款全链）+ `self.run(..., env="conanbuild")` |
| 3 | config.status 写临时目录 Permission denied | umask 077 + HMDFS UID remap（E114） | 生成 configure 中 `umask 077` → `umask 022` |
| 4 | 上游无测试套件 | 无 `tests/`、无 `TESTS=` | `build()` 仍调用 `make check`；输出 `no_tests` 标记；`test_package/` 补 6 条消费者断言 |
| 5 | 包名 bwm 与上游二进制名 bwm-ng 不一致 | 上游历史二进制名 | 同时安装 `bin/bwm-ng` 与别名 `bin/bwm`，测试覆盖两者 |
| 6 | 真机 `autoreconf` 卡在 `aclocal` 报 `126`（`.aclocal-real: No such file`） | automake/1.18 的 `aclocal`/`automake` 包装脚本直接 exec 隐藏的 `.*-real` perl 脚本，其首行写死的构建机 perl 绝对路径在 OHOS 上不存在（无 `/usr/bin/perl`），内核对解释器报 ENOENT（autoconf/2.72 已用 PERL 包装解决同类问题，automake 缺此包装）。第 2 次复检追加证据：`autoreconf` 经 conanbuild 的 `$ACLOCAL` 绝对路径调用 aclocal，单纯 PATH 前置会被绕过 | 本配方新增 `tool_requires("perl/5.42.2")`（与 autoconf/2.72 同版本），`build()` 在 autoreconf 前于 `<build>/.hmos_fix` 生成同名 shims，经 tool perl 绝对路径 exec 同一份隐藏 real，并同时 `export ACLOCAL/AUTOMAKE` 指向 shims（覆盖 conanbuild 的绝对路径）+ PATH 前置；另加 TMPDIR 可写兜底（只读 `/tmp` 时回落到 `<build>/tmp`，复用 HMBS 注入值优先） |
| 7 | configure[139] reports bad bash path, Error 127 (1st attempt) | Repo profile pins CONFIG_SHELL/SHELL to HNP bash which is inaccessible on current HMBS host (capabilities shell=/bin/sh); autoconf re-exec uses CONFIG_SHELL so configure dies before any compile | generate() Environment.save_script override + inline re-export for autoreconf only; Autotools helper still used for configure (FAILED: preflight shows same configure[139] error, override did not win over profile for helper) |
| 8 | Same configure[139] bad bash, 2nd attempt (current) | generate() script did not override profile for Autotools helper internal run; plus _usable_shell could return HNP path via isfile | Abandon Autotools helper: explicit self.run with inline export SHELL/CONFIG_SHELL/TMPDIR AFTER conanbuild sourced for configure/make/check/install via usable /bin/sh; _usable_shell hard-prefers /bin/sh and rejects HNP path |

## 源码修改

无静态补丁文件（`patches_applied: []`）。config.guess/sub 在 autoreconf 之后由配方运行时修补（源码包不含这两份脚本）。

## 上游测试审计

- `src/Makefile.am` / 顶层 `Makefile.am`：无 `TESTS`、`check_PROGRAMS`、`check-local`。
- 源码树：无 `tests/`、`test/` 目录，无 `*_test.c`、`test_*.py` 等测试源。
- `make check`：automake 默认空操作，退出码 0，无实际用例编译/运行。
- 结论：`upstream_tests_exist: false`，`HMBS_UPSTREAM_TEST_RESULT(status=no_tests, discovered=0, executed=0)`，详见 `test_package/MANIFEST.yml` 的 `upstream_test_audit`。
- 证伪要求：消费者测试对 plain/csv 输出做非空与分隔符校验（非“空文件比空文件”）；test.sh 对 `bwm --version/--help` 做关键字断言；ELF/静态链接用 readelf 实测。

## 依赖版本

无外部 Conan 依赖。curses/ncurses 已禁用。构建工具走制品仓 `automake/1.18`、`libtool/2.5.4`，不硬编码本机路径。

## 验证结果

```bash
# test_package/test.sh：6 条断言（待真机预检回填实测数）
bwm --version        # 含 bwm 字样
bwm --help           # 含 usage/options/output 之一
bwm -o plain -d 1 -c 1   # 1 个采样窗口（允许 OHOS 无网卡数据为空，但必须退出码受控）
bwm -o csv -d 1 -c 1     # 同上，CSV 模式
readelf -h bwm       # Type: EXEC 或 DYN
readelf -d bwm       # 无 NEEDED（静态链接）
```

真机预检 evidence（HMBS 后台执行）回填后更新本节；PR 正文「上游测试用例通过率」以预检日志为准。

## 交付物

| 文件 | 说明 |
|------|------|
| bin/bwm-ng | 静态链接 CLI（上游原名） |
| bin/bwm | 同一二进制的包名别名拷贝 |
| share/man/man1/bwm-ng.1 | man 手册 |
| commands.json | R38 命令行工具声明（软件级） |

## 注意事项

- 本包是 CLI 工具，`package_type=application`，必须有软件级 `commands.json`（L0k / R38）。
- OHOS 可能无可用网卡统计；plain/csv 采样允许空输出或退出码 1/2（test.sh 已按受控退出码处理，不记为失败）。
- 构建工具走制品仓 `m4/1.4.19`、`autoconf/2.72`、`automake/1.18`、`libtool/2.5.4`（完整自举链），不硬编码本机路径；`autoreconf` 必须以 `env="conanbuild"` 运行。
- 真机信息（IP/端口/内部命令）仅记录于本 notes.md，不写入 PR 正文；正文统一写「在 HarmonyOS aarch64 环境实测」。

| 9 | 真机 configure 报 C compiler cannot create executables（CC=/data/service/hnp/bin/clang），且 E007 报 config.guess/sub not found | E007 仅查 root/build-aux 漏检，configure 的 umask 077 文本补丁未覆盖 umash/mkdir 回退；编译器失败缺 config.log 证据，无法区分 SDK 路径/-static/只读tmp | 递归 glob 查找 config.guess/sub；umask 补丁改用正则同时覆盖 umask/umash+mktemp/mkdir；build() 新增 _probe_toolchain（CC/CFLAGS/LDFLAGS、clang --version、plain/static 最小编译、TMPDIR 与 /tmp 可写探测）与 configure 失败时 _dump_config_log（12k tail+编译段），TMPDIR 优先级追加 HMBS_TMPDIR/HMBS_INSTALL；仅工作树，未 commit/push |

| 10 | 真机 configure 同一失败第三轮复现（C compiler cannot create executables，旧代码line200、无探针输出），-static 在 LDFLAGS 内毒化 conftest 存疑 | 同源 bwm-ng 同样 -static 进 LDFLAGS 且同样卡 built；cataract/avahi 等过门禁配方均未把裸 -static 放入 configure 期 LDFLAGS；探针设计 plain/static 对照但尚未回传 | generate() 移除 tc.extra_ldflags -static（configure 用干净 LDFLAGS），build() 改为 make -j1 LDFLAGS="$LDFLAGS -static" 仅链接期静态；保留探针与 config.log 取证；manifest 同步；仅工作树，未 commit/push |

| 11 | 探针回传：/data/service/hnp/bin/clang 在真机不存在（ls No such file，conftest rc=127），-static 假设被证伪（plain 与 static 编译同样失败，LDFLAGS 为空） | profile 的 compiler_executables 路径在该 HMBS 宿主失效，与 SHELL 坏路径同类；须换策略：保留 profile 值当文件存在（CI 不变），缺失时回退到真机 PATH/SDK 解析 | 新增 _resolve_compiler（isfile 探测：conf 值优先，其次 PATH、SDK llvm/bin、harmonybrew、usr/local/bin；clang 派生 clang++；无 X_OK 探测），generate/build 双层注入 CC/CXX（env 脚本+inline prefix），探针追加 which 与候选目录清单；仅工作树，未 commit/push |
| 12 | 真机 evidence 判 incomplete（清单表明上游存在测试，no_tests/0 不允许通过；测试命令 make check） | MANIFEST 声明与已合入范例不一致：`upstream_test_in_build: true` + `upstream_test_command: make check` 非空触发清单器存在性判定，且 `upstream_test_audit` 为扁平字符串无法被机器解析覆盖；`build()` 内 `make check` 调用与 marker 与该声明自洽但仍命中同一存在性判定 | MANIFEST 对齐 osmctools/0.9+sipcalc/1.1.6：`in_build: false` + `command: ""` + 结构化 audit（codeload v0.6.3 归档 58 条目实拉验证：无 tests/test 目录、无 *test* 文件、两处 Makefile.am 均无 TESTS/check_PROGRAMS、configure.in 无测试框架注册）；`build()` 删除 `make check` 调用与 marker 输出（含未用 import json），证据改由 test_package 阶段产生；仅工作树，未 commit/push |

| 13 | 真机判 failed（compile，readonly_tmp）：日志含 `touch: cannot touch '/tmp/.bwm_tmp_wtest': Read-only file system` + preflight.sh /tmp 临时文件失败，但 test_package 6/6 与 no_tests 标记实际已输出 | 配方自带 `_probe_toolchain` 主动 `touch /tmp/.bwm_tmp_wtest` 做可写探测，失败字符串被 HMBS 只读门禁误判为构建写入 /tmp；配方本身 TMPDIR 导出与 test.sh 沙盒均已避开 /tmp | 删除探针中的 /tmp 触碰段，仅保留 `$TMPDIR/.bwm_tmp_wtest` 可写探测；构建/测试逻辑与 6 用例 + no_tests 口径不变；仅工作树，未 commit/push |
