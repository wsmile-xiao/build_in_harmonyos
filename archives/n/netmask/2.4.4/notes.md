# netmask 2.4.4 适配笔记

## 编译环境
- 构建系统: autotools（configure.ac + Makefile.am，AM_INIT_AUTOMAKE([foreign])）
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4（aarch64-unknown-linux-ohos，本机 native）
- 状态: built（conan create / W3 验证后回填 published 依据 CI）
- 工具链: autoconf 2.72 (/data/service/hnp/bin) + automake 1.18（tool_requires，制品仓 ohpcd）
- profile: ci/conan/profiles/ohos-aarch64（os=OHOS / arch=armv8 / clang 15）

## 编译步骤（真实探索，2026-09-03 W3 逐条执行）

> 本段为**探索期宿主侧**命令序列记录；进入 conan 干净构建上下文后，自举方式因本机
> HMDFS kernel-exec 限制改为显式解释器直跑链（`autoreconf -fi` 在 conan 上下文不可用），
> 最终 build() 流程与根因见文末「续跑会话处置记录」。本段命令不代表最终配方行为。
```bash
# 源码：Debian official pool orig tarball（sha256 已实测核对）
#   https://deb.debian.org/debian/pool/main/n/netmask/netmask_2.4.4.orig.tar.gz
#   sha256sum == 7e4801029a1db868cfb98661bcfdf2152e49d436d41f8748f124d1f4a3409d83（45775 B）
# 解包后顶层无 configure/Makefile.in（仅 configure.ac/Makefile.am/aclocal.m4/autogen）→ 需自举。

# ① autoreconf 自举（生成 configure + Makefile.in；依赖 automake/1.18 tool_require）
autoreconf -fi            # 实测 exit 0；aclocal/autoconf/autoheader/automake 全部成功

# ② E114 修补（重要！）：生成的 configure/config.status 内嵌
#    `(umask 077 && mktemp -d "./confXXXXXX")`，HMDFS 下 config.status 报
#    "can't create ./confXXXXXX/subs1.awk: Permission denied"（E114/E046 平台限制）。
#    处置：字符串替换去掉 umask 077（见 conanfile._drop_umask_077），实测 configure exit 0。

# ③ configure（in-source；MAKEINFO=true 固化跳过 makeinfo 探测）
CC=clang ./configure --prefix=/ MAKEINFO=true     # exit 0
#    探测全过：syslog.h yes / strerror yes / strtoul yes；config.guess 未触发（native）

# ④ 编译
make -j1                  # exit 0（若未固化 MAKEINFO=true，会因 makeinfo 缺失报
                          #   "makeinfo: inaccessible or not found / Error 127" —— 已规避）

# ⑤ 上游官方测试
make check                # exit 0（TESTS=./testscript，26 个 check 全 ok，0 not ok）

# ⑥ staging 安装验证
make install DESTDIR=$TEST_PREFIX    # exit 0
#    产物：$TEST_PREFIX/bin/netmask + $TEST_PREFIX/share/man/man1/netmask.1
#    netmask.info 因 MAKEINFO=true 不生成（texinfo/makeinfo 在 OHOS 环境缺失，man 已足够）
```

## 遇到的问题与解决方案
| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | python3 直接 exec 报 Operation not permitted | HMDFS chmod 不生效致 exec 失败（SKILL E046 平台限制） | 复制 python3 到可执行目录 tmp/pyenv/bin + chmod 755；pip 安装到 .opendesk/interpreters/pip-global（已在 PATH/PYTHONPATH） |
| 2 | conan HTTPS 报 CERTIFICATE_VERIFY_FAILED | HarmonyOS python OpenSSL 硬编码证书路径无证书文件 | `scripts/install-ca-certs.py` 安装 Mozilla CA 至 usr/local/ssl/cert.pem |
| 3 | Debian orig tarball 无 configure | orig 为 autotools 源包（autogen 脚本提示 autoreconf） | build() 自举：tool_requires automake/1.18（制品仓已发布）+ 显式解释器直跑链（aclocal/automake 用 `perl <am>/bin/.aclocal-real\|.automake-real`，autoconf/autoheader 裸调），不用 `autoreconf -fi`——本机 HMDFS conan 构建子进程无法 kernel-exec 用户目录 shebang 脚本（详见下文「续跑会话处置记录」）；CI Linux 双环境兼容 |
| 4 | makeinfo 缺失 → make 报 Error 127 | 本机/CI 无 texinfo；netmask.1 man 已存在、.info 文档非必需 | configure 注入 `MAKEINFO=true` 固化于 Makefile；make/check/install 全程免 makeinfo |
| 5 | configure 生成后 config.status 失败 (E114) | 生成的 configure 内嵌 `umask 077 && mktemp -d`，HMDFS 目录权限异常 | conanfile `_drop_umask_077` 运行时替换（同 abiword-plugin-clarisworks 3.0.8 先例）；不入 patches/（configure 是构建生成物非上游源） |
| 6 | automake 缺失（aclocal 找不到 Automake::Config） | /data/service/hnp/bin 只有 autoconf 家族 | conan build_requirements tool_requires automake/1.18（制品仓 ohpcd 已发布，本机实测 conan install 可拉取） |
| 7 | make check 个别运行被 SIGTERM | 首次直接 ./testscript 时 run_process 默认 30s 超时（26 check 中含大量 diff 子进程） | conan create / make check 显式较长 timeout（180s+），实测 26 ok 稳定通过 |

## 源码修改
- 无 patches/（conandata patches 为空）。
- build() 运行时修补自举**生成**的 configure（E114：去掉 `umask 077`），该文件是 autoconf
  构建产物而非上游源文件，不入 patches/（与 abiword-plugin-clarisworks/3.0.8 同法；
  SKILL R3 的 refresh-patch 管上游源文件差异）。

## 依赖版本
- build-time tool_requires: automake/1.18（制品仓 ohpcd 发布版）
- 运行时依赖: 空（纯 C，仅 libc：syslog.h/strerror/strtoul 均 libc 能力，OHOS musl 满足）
- 禁止升级：上游 main/2.4.5+ 引入 libcheck（PKG_CHECK_MODULES check），锁定 2.4.4。

## 验证结果
```bash
# make check（= ./testscript，TESTS 26 个 check）—— 全 ok
# 输出摘要（automake 汇总）：
#   # TOTAL: 1   # PASS: 1   # FAIL: 0   # ERROR: 0   （testscript 内 26 ok / 0 not ok）
# 关键断言实跑（W3 实测；2026-09-03 打回补充后 test_package test.sh T1-T16 期望值全部核对一致）：
#   ./netmask 0                              -> 0.0.0.0/32     (T2)
#   ./netmask -c 0                           -> 0.0.0.0/32     (T3, UNVERIFIED 已实测确认)
#   ./netmask 192.168.0.1/255.255.255.0      -> 192.168.0.0/24 (T4)
#   ./netmask -c 192.168.0.1/255.255.255.0   -> 192.168.0.0/24 (T5, UNVERIFIED 已实测确认)
#   ./netmask --cidr 0 2 4 6 8 077777777 0xffffffff  = tests/output_cidr  (T6)
#   ./netmask --standard 0 2 4 6 8                   = tests/output_std   (T7)
#   ./netmask -v                           -> netmask, version 2.4.4 (T8)
#   ./netmask 0 02 0x4 0.0.0.6                    = tests/inputs        (T9)
#   ./netmask 100:200                             = tests/range         (T10)
#   ./netmask 12.34.56.78/20                      = tests/range_cidr    (T11)
#   ./netmask --cisco 0 2 4 6 8 077777777 0xffffffff = tests/output_cisco (T12)
#   ./netmask --range 0 2 4 6 8 077777777 0xffffffff = tests/output_range (T13)
#   ./netmask --hex 0 2 4 6 8 077777777 0xffffffff  = tests/output_hex   (T14)
#   ./netmask 192.168.0.1/0.0.0.0                  = tests/bounds_dq1    (T15)
#   ./netmask 192.168.0.1/0.255.255.255            = tests/bounds_dq6    (T16)
#   （T9-T16 由主编打回补充：以真实编译二进制实跑 + 与 tests/<fixture> 去空白 diff 一致后写入）
```

## 注意事项
1. **make check 在 conan create 内执行**：build() 内 `make check` 已实测通过（26/26）。
   test_package 的 test.sh 为消费侧 R34 smoke test（16 断言 T1-T16，实跑核对一致；
   T9-T16 为主编打回补充，期望值逐条实跑 + 与上游 tests/ fixture 去空白 diff 一致）。
2. **configure 必须 in-source**：automake TESTS=./testscript 以相对路径引用 `./netmask` 与
   `tests/*`，out-of-tree build 目录无 tests/ 会断链。conanfile 不用 basic_layout 分离 build
   （同 b2sum/whois 归档惯例），构建与 make check 均在 source_folder 内进行。
3. **版本红线**：netmask 上游 2.4.5+/main 引入 libcheck 依赖（R36 连锁影响），本包锁定 2.4.4；
   首次适配不造后缀（R37 无历史发布）。
4. sha256 已实测与 Debian 已签名 dsc（netmask_2.4.4-4.dsc）一致，未换非官方源（R39）。
5. W2 原子性：本 PR 仅动 archives/n/netmask/ 目录；软件级 commands.json（R38）已建；
   遗留的 archives/l/libXext 脏改动（历史遗留，不属于本任务）未触碰。

## 续跑会话处置记录（2026-09-03 13:0x-13:2x，G2 FAIL → PASS 全过程）

### 现象与定位（3 轮实测探针，非推断）
1. 复跑 conan-verify（recipe 未改）：G2 稳定复现
   `Can't exec ".../.conan2/p/autom*/p/bin/aclocal": Permission denied
   (Autom4te/FileUtils.pm line 299)` → exit 13。→ 排除"瞬时权限"假设。
2. 关键机理（用探针包 exectest/nmprobe 在 conan create build() 内实测）：
   - conan build 子进程 uid/groups 与交互 shell 完全一致（Uid 20020082,
     Groups 1006 1007 1097 3009 3099）；
   - 但 **HMDFS(/storage/Users/currentUser) 下的 shell 脚本 kernel-exec 被平台拒绝**：
     build 目录新建 #!/bin/sh 的 x.sh `./x.sh` → rc126 Permission denied；
     同一文件 `/system/bin/sh ./x.sh`（显式解释器）→ 正常；
   - ELF 二进制（clang 现场编译的 helf）在 build 目录可正常 exec（rc=42）；
   - /data/service/hnp 下脚本（autoreconf/autoconf/autoheader）可正常 exec；
   - automake/1.18 包内 sh wrapper（aclocal/automake）kernel exec 被拒 → 此前
     `autoreconf -fi` 内部 exec aclocal 失败、`"${ACLOCAL}"` 裸调也失败的根因。
3. 结论：HMDFS+conan 构建子进程上下文的脚本 exec 限制（E046 平台限制变体），
   **对策=全部"显式解释器"调用，不经 kernel exec 脚本**（双向兼容 CI Linux）。

### 最终 build() 流程（conan-verify G2 PASS 实测）
1. aclocal：`perl <am>/bin/.aclocal-real --automake-acdir=<am>/share/aclocal-1.18
   --system-acdir=<am>/share/aclocal --force`
   （必须用 automake/1.18 重建 aclocal.m4——tarball 自带 1.14.1 版，跳过会报
   automake 1.18 "version mismatch ... Automake 1.14.1" exit 63）
2. autoconf：`autoconf -o configure configure.ac`（hnp，裸调）
3. autoheader：`autoheader`（hnp，裸调；AC_CONFIG_HEADERS 出 config.h.in）
4. automake：`perl <am>/bin/.automake-real --libdir=<am>/share/automake-1.18
   --add-missing --copy --foreign`
5. `_drop_umask_077`（E114，保留）
6. configure：`CC=... /data/service/hnp/bin/bash ./configure --prefix=/ MAKEINFO=true`
   （bash 显式解释；config.status 由 configure 内 `$SHELL $CONFIG_STATUS` 调，
   SHELL 已被 profile buildenv 指向 hnp bash）
7. `make -j1`
8. `make check LOG_COMPILER=/data/service/hnp/bin/bash`
   （testscript 的 #!/bin/sh shebang 无法 kernel exec → LOG_COMPILER 让测试统一
   经显式 bash；内部仍 26 ok / 0 not ok）
9. test_package：test.sh 16 项断言 T1-T16 全 PASS（PASS=16 FAIL=0；
   2026-09-03 主编打回后补充 T9-T16 并复跑确认；实测输出见 reports/conan-create.log）

### <am> 目录获取
提交版 conanfile.py 内通过 conanbuild PATH 定位：`AMBIN="$(dirname "$(command -v automake)")"`，
再取 `$AMROOT=dirname $AMBIN` 得包根，PERL5LIB 指向 `$AMROOT/share/automake-1.18`
（tool_requires automake/1.18 的 bin 已由 conanbuildenv 注入 PATH，实测返回
.conan2/p/autom*/p）。`self.dependencies.build["automake"].package_folder`
（Conan 2 tool_requires build context API）同样是可行取法。
提交版 conanfile.py 无平台分支：该定位方式在 CI Linux 同样成立（conanbuildenv
PATH 同样注入 automake bin），无需 `${ACLOCAL:-aclocal}` 类回退。
---

**编译结束**: 2026-09-03 13:43
**最终状态**: built

---

### 后续修订记录（2026-09-03 16:5x，test_package 扩至完整复刻上游 26 个 check）

主编进一步要求：上游用例 26 个（testscript 26 check），适配后 test_package 不得缩水。
处置：test.sh 由 T1-T16（16 项）重写为**与上游 testscript 一一对应的 26 个 check**
（编号 1-26），并新增 `test_package/fixtures/`（上游 v2.4.4 tests/ 26 个期望文件的
逐字节拷贝，sha256 对拍一致）。每条用例真实执行 netmask 二进制，stdout 与对应
fixture `diff -au`（与上游 `eval $3 | diff -au $2 -` 同语义），不再使用去空白近似比较。

验证：以 W3 make check 26/26 ok 的同源产物二进制（tmp/builds/netmask-2.4.4.work/netmask）
实测新 test.sh → `ok 1..26` 全过、`UPSTREAM_CHECKS=26 PASS=26 FAIL=0`、RC=0。
MANIFEST.yml `assertion_count` 16→26，conanfile.py docstring 同步。
git 提交 d10007bfb（本地，未 push）。
