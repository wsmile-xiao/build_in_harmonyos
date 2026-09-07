# posh 0.14.6 适配笔记

## 编译环境
- 构建系统: autotools（tarball 无预生成 configure，Debian 模式 autoreconf -fi 自举）
- 编译日期: 2026-09-03
- 编译器: clang 15.0.4（/data/service/hnp/bin/clang，profile conf 注入）
- 状态: built

## 编译步骤

```bash
cd /storage/Users/currentUser/tmp/builds/posh-0.14.6.work
# 1. 自举（tarball 无 configure；Debian debian/rules 同款）
CONFIG_SHELL=bash autoreconf -fi
# 2. 修复生成 configure 的 umask 077（E011/E114，HMDFS 下 config.status
#    0700 临时目录不可写 → "could not setup config files machinery"）
sed -i 's/umask 077/umask 022/g' configure
# 3. 配置（config.guess 原生探测 aarch64-unknown-linux-ohos，禁 --build/--host）
CONFIG_SHELL=bash bash ./configure --prefix=/storage/Users/currentUser/usr/local
# 4. 构建 + staging 安装
make -j8 && make install DESTDIR=/storage/Users/currentUser/tmp/test-install-posh-0.14.6
# 5. 上游 th 测试（见下文）
```

产物：`bin/posh`（arm64 ELF，musl 动态链接）+ `share/man/man1/posh.1`。零依赖、零源码补丁。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | config.status 报 `could not setup config files machinery`（confXXXXXX/subs1.awk Permission denied） | E011/E114：autoconf 生成的 configure 用 `umask 077` 建临时目录，HMDFS UID 映射 setgid 下 drwx--S--- 属主不可写 | sed 生成的 configure umask 077→022（poke 0001 补丁同款文本变更；configure 为生成文件，固化在 conanfile.py build() 内，非补丁形式） |
| 2 | th 框架启动即 `couldn't make directory /tmp/rtd$$ - Read-only file system` | th 硬编码 /tmp 路径（第 190-194 行），OHOS /tmp 只读（E002） | 复制 th 到可写位置并重定向 /tmp 字面量（源码树不动），perl 直跑（th-sh 即找 perl 后 exec） |
| 3 | TMPDIR 注入后 th 仍有 27 个 unexpected 失败（heredoc/token 系列全挂） | th 对被测 shell 只传环境白名单（HOME/LD_LIBRARY_PATH/LOCPATH/LOGNAME/PATH/SHELL/USER），TMPDIR 被剥离 → posh heredoc 临时文件回退 /tmp 失败（posh 尊重 $TMPDIR，var.c V_TMPDIR） | th `-e TMPDIR=<可写目录>` 显式注入 → 失败从 27 降到 2 |
| 4 | CI 环境跑 autoreconf -fi 会失败 | CI sandbox 有 autoconf（/data/service/hnp/bin）但缺 automake/aclocal | conanfile.py `tool_requires("automake/1.18")`（abiword-plugin/adplay 先例；posh 无 LT_INIT 不需要 libtool） |

## 源码修改

**无**。.orig 基线 93 文件逐一 diff 验证零修改。umask 修正作用于 autoreconf 生成的 configure（tarball 不含该文件，无法作为补丁），在 conanfile.py build() 内固化（autoreconf 后文本改写 umask 077→022，abiword-plugin-clarisworks/adplay 同款先例）。

**config.guess/config.sub 的两种环境（易混淆，务必区分）**：
- 本机手动探索：autoreconf 取本机 OHOS 适配版 automake 的 config.guess（autoconf 2.72 系），**原生识别** aarch64-unknown-linux-ohos，手动步骤无需任何处理；
- conan 构建（CI 同路径）：autoreconf 取 tool_requires `automake/1.18` 包的原版 GNU config.guess/config.sub，**不含 HarmonyOS 支持且用 umask 077**（E007+E011）→ conanfile.py build() 在 autoreconf 后就地注入 HarmonyOS uname 分支、__OHOS__ LIBC 探测、ohos-linux 三元组并放宽 umask（同 patch-autotools-ohos.pl 语义；R8 平台宏禁令的豁免项：config.guess 内 __OHOS__ 探测）。修正带标记校验，标记未落地即抛 ConanException 拒绝静默失败。全新强制构建已验证注入生效（HarmonyOS=True / ohos-linux=True）。

patches/ 为空。

## 上游 quirk（保持一致，不修改）

**POSH_VERSION 忘 bump**：acinclude.m4 仍定义 `define(POSH_VERSION, 0.14.5)`，0.14.6 发布时维护者忘记更新。后果：二进制 `$POSH_VERSION` 报 0.14.5；上游 `tests/version.t` 期望值同为 0.14.5。**决策：保持与上游一致不修改**（改了反而偏离上游测试预期）。测试断言写法兼容：test.sh T1 接受 0.14.5 或 0.14.6 并注明原因。另注：posh 无 -version/-V/--version 命令行选项，版本只能经 `$POSH_VERSION` 变量查询（这正是上游 version.t 的测法）。

## 依赖版本

- 运行时依赖：无（W0 preflight EXIT=0 零依赖）
- 构建依赖：autoconf 2.72 + automake 1.16.5（本机）；CI 侧 automake/1.18（tool_requires）+ 系统 autoconf
- 测试框架：perl 5.42.0（th 上游测试用；CI 不复现，见 MANIFEST.yml）

## 验证结果

### 上游 th 测试（tests/th-sh，真实执行）

CATEGORIES_TO_TEST=sh,posix,pdksh,posh,debian,no-history,no-typeset,no-aliases,no-arrays,no-coprocs,no-herestrings,no-ulimit（tests/Makefile.am 原样）。执行方式：th 复制到可写目录重定向 /tmp 字面量 + `-e TMPDIR` 注入（th 环境白名单不含 TMPDIR），perl 直跑（th-sh 即找 perl 后 exec）。

```text
Total failed: 14 (2 unexpected)
Total passed: 216
```

- **216 pass / 12 expected-fail**（pdksh 系 shell 在 posh 剥离语义下的预期失败，框架标记 "as expected"）
- **2 unexpected-fail，均已归因、非移植缺陷**：
  - `mksh.t:utilities-getopts-2`：posh 的 getopts 在 `?` 后不重置 OPTARG（上游 getopts 实现与 mksh/pdksh 期望语义的分歧，libc 无关）
  - `utilities.t:utilities-8`：umask 内建报错消息为 musl getopt 格式 `umask: unrecognized option: r`，测试期望 glibc 格式 `umask: invalid option -- 'r'`（libc 消息格式差异，功能等价）

### 冒烟验证（staging 二进制，后被 test_package/test.sh 固化为 19 断言）

```bash
$ posh -c 'echo $((3*7+1))'          # 22
$ posh -c 'x=hello; echo ${x}world'  # helloworld
$ posh -c 'exit 42'; echo $?         # 42
$ posh -c 'echo $POSH_VERSION'       # 0.14.5（上游忘 bump，见上）
```

## 交付物

| 文件 | 说明 |
|------|------|
| bin/posh | POSIX shell 二进制（arm64 ELF） |
| share/man/man1/posh.1 | 手册页 |

## 注意事项

- heredoc 依赖 TMPDIR：/tmp 只读（E002）环境运行含 heredoc 的脚本前需设置 TMPDIR（posh 尊重该变量）
- conan create 必须同时传 `-pr:h` 和 `-pr:b`（tool_requires automake 用 build profile 解析）
- make 在 CI 上用 -j1（E074 HMDFS jobserver fifo EPERM 预防，abiword-plugin 先例；本机 -j8 可过，CI 保守）
---

**编译结束**: 2026-09-03 17:24
**最终状态**: built
