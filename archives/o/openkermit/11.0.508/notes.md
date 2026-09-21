# openkermit 11.0.508 适配笔记

## 编译环境
- 构建系统: makefile（上游单文件手写巨型 makefile，9858 行，无 autoconf/CMake/Meson）
- 编译日期: 2026-09-18
- 编译器: clang（Conan `tools.build:compiler_executables` → `/data/service/hnp/bin/clang`）
- 目标: OHOS / HarmonyOS PC aarch64（musl，`aarch64-linux-ohos`）
- 状态: built

## 源码信息
- 上游仓库: **https://github.com/OpenKermit/ckermit**（官方；任务书所写 `kermitproject/ok` 经 GitHub API 核验不存在）
- tag: `v11.0.508`（2026-08-10 发布，commit 4d93586194057ddab576617dc9e5065489dc7d45）
- 归档: `https://codeload.github.com/OpenKermit/ckermit/tar.gz/refs/tags/v11.0.508`
- sha256: `252f716bbac57d0a665a0c087f18abab095acc8369786cd08d1dde831ecd4747`
  （本地计算值与官方 release 资产 SHA256SUMS 双源一致）

## 编译步骤

```bash
# 补丁（1 个，见下）
# 构建（等价于上游官方 musl 目标 makefile:7336 `linux+musl`）
make xermit \
  CC=/data/service/hnp/bin/clang CC2=/data/service/hnp/bin/clang \
  CFLAGS="-O2 -DLINUX -pipe -funsigned-char -DFNFLOAT -DCK_POSIX_SIG -DCK_NEWTERM \
          -DTCPSOCKET -DLINUXFSSTND -DNOCOTFMC -DPOSIX -DUSE_STRERROR \
          -DHAVE_PTMX -DHAVE_OPENPTY -DNOCURSES -DNOGETUSERSHELL -DNOARROWKEYS" \
  LIBS="-lm" SHELL=/data/service/hnp/bin/bash -j1
# 产物 ./wermit → 打包为 bin/kermit；COPYING.TXT → licenses/
```

关键点（为什么这样编）：

- **直接调 `xermit`，不调 `linux`**：`linux` 目标做的是 `ld -lXXX` 与 `grep /usr/include/*`
  主机探测，交叉环境下无意义。上游自己的 musl 目标（`linux+musl`，makefile:7336）
  就是「直接调 `xermit` + 显式 `CFLAGS`」，本配方沿用该**官方** pattern。
- **`CC`/`CC2` 可覆盖**：makefile:961 缺省 `CC= cc` `CC2= cc`（不是 gcc）；
  `linuxa` 用 `"CC=$(CC)" "CC2=$(CC)"` 转发，`xermit` 规则用 `$(CC2)` 链接、
  `$(CC) $(CFLAGS) -DKTARGET=... -c` 编译（makefile:1028）。故 9.0.302 时代的
  **gcc shim 在 11.0.508 的 xermit 路径上不需要**（已实测：全程无 gcc 调用）。
- **NOCURSES 裁剪**：不定义 `CK_NCURSES`，`ckuusx.c` 的 `<curses.h>/<ncurses.h>`
  分支不参与编译；同时 `-DNOCURSES` 让 `ckuus5.c` 把 "NOCURSES" 登记进版本特性串。
  产物 `NEEDED` 仅 `libc.so`（`llvm-objdump -p` 实测），零第三方动态库依赖。
- **musl 三项**：全部用编译器宏解决，**零源码补丁**（除下述 pty 一项）：
  - `-DNOGETUSERSHELL` → `ckcdeb.h:6858/6904` 的 `#ifndef` 守卫不再定义 `GETUSERSHELL`，
    `ckufio.c:7984` 的 `getusershell()` 调用被 `#ifdef GETUSERSHELL` 排除（musl 无此函数）。
    注意 11.0.508 的平台块（IRIX/PTX/AIXRS/SINIX/UNIXWARE/COHERENT）没有 OHOS 分支，
    但编译器宏比打补丁更干净，故不打 ckcdeb.h 补丁。
  - `-DNOARROWKEYS` → `ckucmd.c:7659/7676` 的 `stdin->_cnt` 窥探分支被排除，改走 `conchk()`。
    （上游 `ckcdeb.h:147` 在未定义 `DOARROWKEYS` 时已自动定义 `NOARROWKEYS`；本配方仍显式传入，
    以钉住行为、防止上游未来把默认值翻成 `DOARROWKEYS`。）
  - `CK_VHANGUP` 见下（唯一补丁）。
- **R9**：全程 `-j1`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `conan create` 在 `source()` 报 `BadZipFile: File is not a zip file` | codeload URL 末段是 tag 名（`…/tar.gz/refs/tags/v11.0.508`）不带扩展名，Conan `get()` 推出去文件名 `v11.0.508`，`unzip()` 无法按扩展名选 tar.gz 解码器而退回 zip 解码器 | `conandata.yml` 的 `sources:` 增加 `filename: "ckermit-11.0.508.tar.gz"`（仓内已有 abbtr/abcmidi 先例），文件名显式化后正常解压；sha256 不变 |

## 源码修改

1 个补丁（`patches/`，实质平台分支，R8 合规——无 `__OHOS__` 平台宏）：

1. **0001-ckupty.c-libc-vhangup.patch**：`ckupty.c` 在 `#ifdef LINUX` 下无条件定义
   `CK_VHANGUP` 并调用 `vhangup()`（musl 无此函数）。补丁把该 `#define` 收进
   `#ifdef __GLIBC__`，musl/OHOS 上改走已探测到的 `HAVE_OPENPTY` pty 路径。
   与 9.0.302 的 `0003` 同解法。

> 与 9.0.302 的差异：9.0.302 需要 3 个补丁（ckcdeb.h NOGETUSERSHELL / ckucmd.c stdio-musl /
> ckupty.c no-vhangup）；11.0.508 上游已把前两项改成可被编译期宏控制（分层 `#ifndef`），
> 故只剩 pty 一项需要落补丁。

## 依赖版本

无外部依赖（纯 C；`libm` 随 musl 进 `libc.so`）。**不依赖 ncurses**（NOCURSES 裁剪），
不依赖 OpenSSL/crypt/resolv/lockdev（`linux` 探测路径的选项在本适配中未启用）。

## 上游测试审计与执行（rule4）

**2026-09-19 再修改**：原稿把「上游 428 例未执行」归因于「环境缺 libcheck / pytest」，未按官方口径补依赖真跑（Septest 意见：「缺依赖补依赖，上游测试用例通过率不达标」）。本次按官方要求先查制品仓/环境，**补齐依赖并真跑上游全套**。

### 补齐的依赖

| 依赖 | 补齐方式 |
|------|----------|
| libcheck（`make check` 的 C 单元测试框架） | 制品仓已有 **`check/0.15.2`**（OHOS armv8 静态包）：`conan install --requires=check/0.15.2 -pr:h ci/conan/profiles/ohos-aarch64` |
| pytest / pyftpdlib / pytest-timeout / pytest-xdist | `python3 -m pip install`（私有 PyPI 镜像可得） |
| 可写临时目录 | OHOS 根文件系统只读，`/tmp` 不可写（EROFS）；libcheck 的父子进程通信需临时文件，故以 `TMPDIR/TMP/TEMP` 指向可写目录 |

### 真跑结果（实测口径）

| 套件 | 上游规模 | 真跑结果 |
|------|----------|----------|
| pytest 集成测试 `tests/test_*.py` | 32 文件 / 300 个 `def test_`；**pytest 参数化后采集 1792 个用例** | **1137 passed / 1 failed / 645 skipped / 9 xfailed** |
| libcheck 单元测试 `tests/unit/*.c` | 8 程序 / 132 个 `tcase_add_test`（运行时 120 条断言） | **111 断言通过 / 9 失败** |
| `.ksc` 脚本 | 3 个（由 `tests/test_scripting.py` 的 4 个 pytest 用例驱动） | 4 passed（已计入 pytest） |

**合计：执行 1258 例，通过 1248，失败 10 ⇒ 通过率 99.2%；跳过 645 例（逐类归因见下）。**

### 跳过原因（pytest `-rs` 逐条聚合）

| 例数 | 原因 | 性质 |
|------|------|------|
| 400 | `ckermit-old-9.0.302` 二进制不存在（互操作用例） | 环境无对端参考实现（上游 `tests/compat-binaries.sha256` 声明的独立产物，不在源码包内） |
| 128 | 本构建未启用 SSL/TLS | 本适配功能裁剪（零第三方动态库路线） |
| 49 | `lrzsz (sz/rz)` 不可用 | 环境无 lrzsz（制品仓无配方） |
| 29 / 23 | `gkermit` / `eksw` 二进制不存在 | 环境无对端参考实现 |
| 15 | 本构建未启用 VSOCK | 本适配功能裁剪 |
| 1 | 本环境无同时具备 link-local 与另一 IPv6 地址的网卡 | 环境限制 |

### 失败逐条归因（10 例，全部为测试对环境的硬编码假设，非适配缺陷）

- `tests/unit/test_zfnqfp.c` 6 例：用例**硬编码 `mkdtemp("/tmp/zfnqfpXXXXXX")`**，OHOS `/tmp` 只读 → `mkdtemp` 返回 NULL。
- `tests/unit/test_net.c::test_getfqhostname_v6_*` 3 例 + `tests/test_ipv6.py` 1 例：断言假设 `::1 → localhost`，本机 `/etc/hosts` 为 `::1 → ip6-localhost`（Debian 惯例）。

> 证据（含逐条断言原文）：`learninglog/20260912openkermit-11.0.508/remod-20260919/`（`unit-tests-run.log`、`pytest-full-r4.log`、`pytest-full-r5-rs.log`、`上游测试执行报告.md`）。

## 验证结果

```bash
# conan create（rc=0）
conan create archives/o/openkermit/11.0.508 -pr:h ci/conan/profiles/ohos-aarch64 --build=missing
# test_package: 37/37 断言通过
#   HMBS_TEST_PACKAGE_RESULT={"executed":true,"passed":true,...,"discovered":37,"passedCount":37}
#   HMBS_UPSTREAM_TEST_RESULT={"status":"complete",...,"upstream_suite_result":"pytest 1137 passed / 1 failed / 645 skipped / 9 xfailed; libcheck 111/120 assertions passed; total executed 1258, passed 1248 (99.2%)",...}
```

- 编译状态：通过
- 上游测试用例通过率：**1248/1258（99.2%）**（pytest 1137/1138 + libcheck 111/120；跳过 645 例与失败 10 例逐类归因见上）
- 新增测试用例通过率：37/37（100%）

## 交付物

| 文件 | 说明 |
|------|------|
| bin/kermit | OpenKermit 11.0.508 可执行文件（上游 `wermit` 改名） |
| licenses/COPYING.TXT | BSD-3-Clause 许可证文本 |

## 注意事项

- `test_kermit.sh` 用 `command -v kermit` 定位二进制（VirtualRunEnv 提供 PATH），
  所有调用都带 `-Y`（禁用 init 文件）并 `< /dev/null`，避免非交互环境挂起。
- `test_kermit.sh` 内对上游脚本路径用 `BASH_SOURCE` 推导，
  不依赖 `test()` 的 cwd。
- `test_control.ksc` 内部用 `directory /nonexistent_directory_xyz` 触发失败分支，
  输出会带一行 `?No files match`/语法错误提示——这是上游脚本的设计意图
  （`if failure` 的触发源），不是缺陷；上游 pytest 同样只断言 `FAILURE verified`。
- 上游脚本在 `tests/scripts/` 下，**未修改、逐字节复制**到 `test_package/scripts/`
  （sha256 见 MANIFEST.yml），安装产物中不含测试文件。
