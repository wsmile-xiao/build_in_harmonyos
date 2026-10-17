# pipexec 2.6.2 适配笔记

## 编译环境

- 构建系统：GNU autotools（`configure.ac` + automake `Makefile.am`/`Makefile.inc` + libtool）
- 适配日期：2026-09-27
- 本机验证环境：Ubuntu 24.04 容器（GNU autotools + gcc），另用 OHOS clang 15.0.4
  （DevEco Studio SDK `default/openharmony/native/llvm`）做交叉编译探针
- 目标平台：HarmonyOS / OpenHarmony PC aarch64，musl libc
- 状态：built（本机 B 阶段全通过；真机 shadow CI 未执行，命令见文末）

## 上游与源码核验（W0）

| 项 | 结果 |
|---|---|
| 上游仓库 | `florath/pipexec` 已 404；同名项目现位于 **`flonatel/pipexec`**（GitHub 搜索 + release 核对确认） |
| 目标版本 | 2.6.2（tag 存在，2024-10-16 发布，release asset `pipexec-2.6.2.tar.xz`） |
| release asset URL | `https://github.com/flonatel/pipexec/releases/download/2.6.2/pipexec-2.6.2.tar.xz`（HTTP 200） |
| release asset sha256 | `d3ba6802a9dc4e5f336e840958c4ddaf3de427fa70a62430688c91e4d46e3d1d`（347780 B，XZ） |
| license | GPL-2.0-or-later（`LICENSE` 为 GPL-2 正文；`src/pipexec.c` 头注释 SPDX `GPL-2.0-or-later`） |
| 归档选择 | release asset 含生成好的 `configure`/`Makefile.in`/`aclocal.m4`/`config.h.in`；tag archive 不含（会触发 CI 无法执行的 autoreconf）→ 选 release asset |
| 源码构成 | `src/` 6 个 .c（pipexec 549 行、pipe_info 245、peet 236、logging 226、ptee 101、command_info 79）+ 4 个 .h；`test/basic_tests.sh`(35 行) + `test/ptest.c`(14 行) |
| 历史归档（W0b） | `archives/p/` 下无 pipexec 目录，本仓库首次适配，无历史 notes 需比对 |
| ConanCenter | `recipes/pipexec/` 不存在 → 无上游社区配方参考 |
| 语言判定 | 纯 C99（`-std=c99`），无 C++/Rust/Go |

## 依赖核验（W0 / R35 / R36）

`configure.ac` 的库检查段为空（只有 `AC_PROG_CC`、`AM_PROG_AR`、`LT_INIT`）；
源码 `#include` 仅标准头（`unistd.h`/`stdio.h`/`stdlib.h`/`string.h`/`errno.h`/
`fcntl.h`/`poll.h`/`signal.h`/`time.h`/`sys/wait.h`/`sys/types.h`/`sys/stat.h`/
`assert.h`/`stdarg.h`/`syslog.h`/`stdbool.h`/`stddef.h`），无 glibc 专属符号
（`pthread_cancel`/`fexecve`/`strdupa`/`getline`/`error()`/`fts.h` 等一概未用）。

- **Conan 依赖集合 = 空**（`requirements()` 为 `pass`）→ 无 R36 依赖发布阻塞。
- 全程未使用 `--build=missing` 绕行、未用本地缓存顶替。

## 编译步骤（实际执行顺序）

```sh
# 本机（容器内）等价验证
tar -xf pipexec-2.6.2.tar.xz                      # 得到 pipexec-2.6.2/
cd pipexec-2.6.2
patch -p1 < .../0001-config-guess-sub-ohos.patch
patch -p1 < .../0002-configure-respect-user-cflags.patch
patch -p1 < .../0003-version-gen-portable-shell.patch
# 固定 autotools 输入/生成物时间戳（见问题 #4）—— 配方 build() 自动完成，
# 手工复现时按输入 < aclocal.m4 < configure/Makefile.in 三个递增时间戳赋值
touch -d '2000-01-01' configure.ac Makefile.am aclocal.m4 src/Makefile.inc \
      test/Makefile.inc m4/*.m4
touch configure Makefile.in config.h.in config.guess config.sub
mkdir build && cd build
../configure --prefix=$PWD/../prefix            # out-of-tree
make -j2
make check                                       # 上游 TESTS 为空，正常
make install
bash ../test/basic_tests.sh                      # 上游测试，cwd=build 目录

# 目标环境（真机 shadow CI，待执行）
conan create archives/p/pipexec/2.6.2 \
    -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64 \
    --user=ohpcd --channel=stable
```

## 遇到的问题与解决方案

| # | 现象（首个错误原文） | 根因 | 解决方案 | 重新验证 |
|---|---|---|---|---|
| 1 | `./config.guess: unable to guess system type`（configure 在 "checking host system type" 处中断，`uname -s`=HarmonyOS） | 上游 `config.guess` timestamp 2018-02-24，无 HarmonyOS 分支；`config.sub` 不认 `linux-ohos`（知识图谱 **E007** 命中） | `patches/0001-config-guess-sub-ohos.patch`：加 `*:HarmonyOS:*:*)` 分支（`echo aarch64-unknown-linux-ohos; exit`）+ `config.sub` 的 `linux-ohos`/`ohos-linux` 三元组；**不用 --build/--host**（E007 明令禁止） | 模拟 HarmonyOS uname：`config.guess` → `aarch64-unknown-linux-ohos`；`config.sub aarch64-linux-ohos` → `aarch64-unknown-linux-ohos`；`aarch64-linux-gnu` 回归正常 |
| 2 | 生成的 Makefile 丢失外部 CFLAGS（外部标记 `-DPIPEXEC_USER_CFLAGS_SEEN=1` 不出现在 `CFLAGS = `） | `configure.ac` 末尾**无条件赋值** `CFLAGS="-std=c99 ${COMMON_FLAGS}"`、`CXXFLAGS=…`，覆盖 conan `AutotoolsToolchain` 注入的 `--target/--sysroot/-fPIC` | `patches/0002-configure-respect-user-cflags.patch`：两处改为追加 `CFLAGS="$CFLAGS …"`（同 `archives/l/libnova/0.16`） | 生成的 Makefile `CFLAGS = -O0 -DPIPEXEC_USER_CFLAGS_SEEN=1 -std=c99 -Wall -Wextra -Werror -O3`；交叉编译探针用 OHOS clang 全部源文件 `-Werror` 零告警通过 |
| 3 | `make` 报 `/bin/sh … build/version-gen.sh` 无法执行（真机上 `/bin` 不存在、`/bin/sh` 不在 PATH） | `src/Makefile.inc` 写死字面 `/bin/sh`；生成的 `version-gen.sh` 经 `#!/bin/sh` 调 `version.sh`（知识图谱 **E165** 命中） | `patches/0003-version-gen-portable-shell.patch`：改用 `configure` 填充的 `$(SHELL)`，并直接 `cat version.txt`（上游 `version.sh` 本就只 cat 它） | `make` 通过，`src/app_version.c` 内容为 `char const app_version[] = "2.6.2";` |
| 4 | `make` 报 `missing: line 81: autoconf: command not found` → `Error 127`（重跑 autoreconf） | 补丁重写了 `configure.ac`/`Makefile.inc`/`config.guess`，刷新 mtime 后 `make` 认为 `configure`/`Makefile.in`/`aclocal.m4` 过期，要重生成（CI 镜像无 autoconf/automake） | 配方 `build()`：沿真实依赖链赋三个**递增的过去时间戳**——输入（configure.ac/Makefile.am/*.inc/m4/*）= `946684800` ＜ `aclocal.m4` = `946684900` ＜ configure/Makefile.in/config.h.in/config.guess/config.sub = `946685000`。（注意不能给所有生成物同一个「当前时间」：`aclocal.m4` 既是 configure.ac 的产物又是 Makefile.in 的依赖，同值会让它显得比 Makefile.in 新而再次触发 aclocal/automake） | `make` / `make install` / 上游测试全部通过（未再触发 autoreconf）；用**真实 conanfile.py** 在容器内驱动 `build()` 复验通过 |
| 5 | `test/basic_tests.sh` 里 `./bin/pipexec … [ A /bin/true ]` 在 OHOS 无 `/bin/true` | 上游测试脚本用 `/bin/*` 绝对路径，HarmonyOS 无传统 `/bin`（E165） | 配方 `build()` 运行前按 `shutil.which()` 把 `/bin/true|false|echo|cat|grep` 重定向到本机绝对路径；断言与脚本其余内容不变 | 本机 4/4 通过（Linux 上 `/bin/*` 已存在，重定向为 no-op） |

**未改动上游 C 源码**（第 3 条的 `version-gen.sh` 属构建脚本，非程序源码）：6 个 `.c`
在 OHOS clang 15 + `-Wall -Wextra -Werror -O3` 下零告警（见「交叉编译探针」）。

## 真机 shadow CI 迭代记录（W5）

设备：HarmonyOS / HongMeng Kernel 1.12.0 / aarch64；单包排队，全局锁 `device-global.lock`。
job `pipexec-2.6.2-20260927`；runner `ohos-test-runner.sh --mode heavy`（自动加锁）。

| 轮次 | 现象（首个错误原文） | 根因 | 解法 | 结果 |
|---|---|---|---|---|
| r1 | `ci/conan/build_and_test.sh:980: permission denied: bash` → `[fail] KC` | 隔离 job 的登录/runner PATH 里没有 bash（设备 bash 在 `/data/service/hnp/bin`） | 运行时 `export PATH=/data/service/hnp/bin:$PATH`（同设备既有 job 的 env.sh 做法） | L0 通过；KC 因缺 bash 阻塞 |
| r2 | `[step] KC ... [OK]` 通过；`conan create` 在 `autotools.configure()` 报 `Error 126`：`/system/bin/sh: .../configure: Permission denied` | **E232**：源码树在 HMDFS 上不可执行；`CONFIG_SHELL` 包不住 Conan 首次启动 configure | 配方按 E232：`settings_build.os==OHOS` 时 `/system/bin/sh <configure> <autotools._configure_args>` + `generate()` 固定 SHELL/CONFIG_SHELL（同 opusfile 0.12） | E232 修复生效，configure 能启动 |
| r3 | `./config.status: line 816: ./confSWaAEu/subs1.awk: Permission denied` | **E114**：HMDFS 上 `(umask 077 && mktemp -d ./confXXXXXX)` 产出 `drwx--S---` 目录，属主不可写 | 补 `patches/0004-configure-hmdfs-mktemp.patch`：mktemp 引导换 `mkdir -p`（同 pipemeter 1.1.5 补 0002）；本机实测生成的 `config.status` 同步继承 | r4 通过 |
| r4 | —（无新错误） | — | E232 配方分支 + 补丁 0004 | **exit code 0，Success 1/1，全门禁通过** |

> 说明：r1 的 PATH 问题是**设备运行环境**，非配方问题；r2/r3 是**适配缺口**，落成配方分支
> （E232）与补丁 0004（E114），均为 OHOS/HMDFS 专属、不影响 Linux。

### 真机最终结果（r4）

```text
job            : pipexec-2.6.2-20260927（run 195545，lock wait_seconds=0）
conan create   : Success 1/1，exit code 0
L0_RESULT      : pass: all checks passed
L1_RESULT      : pass: test_package executed
L1e            : [ok] Negative test confirmed — test genuinely depends on pipexec（非假测试）
L2_RESULT      : skip: peet/pipexec/ptee version/help failed（非阻塞；上游 usage() 一律 exit 1）
L4_RESULT      : warn: dangerous functions in patches（误报，见下）
L5_RESULT      : pass: bin/ has content
上游测试        : test/basic_tests.sh 4/4 passed（discovered 4, executed 4, failed 0, skipped 0）
                /bin 工具已重映射：/bin/{cat,echo,false,grep,true} -> /system/bin/*
test_package   : pipexec-smoke-ok 11/11（T1–T11 全 PASS，对已安装包内二进制）
产物            : bin/{pipexec,ptee,peet}；ELF shared object, 64-bit LSB arm64,
                dynamic (/lib/ld-musl-aarch64.so.1)（bin/ptest 已按 package() 剔除）
```

**L4 warn 是误报**：CI 的 L4 用 `grep -rlE '(strcpy|sprintf|gets|strcat)\b'` 扫补丁；
`gets\b` 命中的是上游 `config.guess` 上下文行里的英文单词 **"tar·gets"**
（`# NetBSD (nbsd) targets should ...`）。补丁 0001 只新增 HarmonyOS 分支，未引入任何
危险函数。非阻塞，不修改。

## 源码修改

3 个补丁均由「对 pristine tarball 快照做定向 unified diff（`-p1`）」生成，
**不含任何 `__OHOS__` 平台宏**（R8 / PF5），不引入 `/usr/local` 等共享前缀字面量（R49 / PF6）：

- `patches/0001-config-guess-sub-ohos.patch` — config.guess `+10`，config.sub `+5/−2`（portability，E007）
- `patches/0002-configure-respect-user-cflags.patch` — configure.ac / configure 各 `+2/−2`（portability）
- `patches/0003-version-gen-portable-shell.patch` — src/Makefile.inc、Makefile.in 各 `+1/−1`，
  build/version-gen.sh `+3/−1`（portability，E165）

补丁 SHA256 记录在 `conandata.yml` 与版本 manifest；每个补丁都已用 `patch -p1` 干净应用复验。

## 交叉编译探针（OHOS clang）

用 DevEco SDK 的 OHOS clang 15.0.4 对全部源文件做 `--target=aarch64-linux-ohos
--sysroot=<SDK>/sysroot -std=c99 -Wall -Wextra -Werror -O3` 编译：

```
src/pipexec.c OK / src/logging.c OK / src/version.c OK / src/command_info.c OK
src/pipe_info.c OK / src/ptee.c OK / src/peet.c OK / test/ptest.c OK
```

零告警通过 → 上游 `-Werror` 在 OHOS clang 上不是问题（**E063 未命中**）。
产物确认为 `ELF64 / AArch64`。注意上游 `#include "src/xxx.h"` 需 `-I.` 即源码根为 include 根
（automake `DEFAULT_INCLUDES = -I.` 已满足）。

## 发现与知识

本包障碍全部命中知识图谱既有条目或属于构建系统通用处理（R30 命中即复用；本次未新增草稿）：

- ✅ **E007**：config.guess/sub 不识别 HarmonyOS → 补 `0001`（并记录该版本分支必须 `echo …; exit` 收尾的坑）
- ✅ **E165**：HarmonyOS 无 `/bin`，脚本 shebang/字面 `/bin/sh` 失效 → 补 `0003`（构建脚本改 `$(SHELL)`）+ 配方内对上游测试的 `/bin/*` 重定向
- ✅ configure.ac 无条件覆盖 CFLAGS 丢 `--target/--sysroot`：属 autotools 类通用构造，采用 `archives/l/libnova/0.16` 的 respect-user-cflags 同型修正
- ✅ 补丁刷新 autotools 输入 mtime 触发缺失的 autoreconf：沿依赖链赋三个递增过去时间戳（输入 ＜ aclocal.m4 ＜ configure/Makefile.in）固定，思路源自 `archives/l/libmodbus/3.2.0`；**须注意 aclocal.m4 既是 configure.ac 的产物又是 Makefile.in 的依赖**，给全部生成物同一个「当前时间」会让它反超 Makefile.in
- ✅ pipexec 2.6.2 语义：**fan-in/fan-out 不可表达**（`pipe_info_check_for_duplicates` 拒绝重复 pipe 端，报 `Duplicate pipe in command line`），且**仅在子进程异常终止（信号/非正常退出）时重启**（源码 `set_restart(1)` 位于 `!WIFEXITED(status) || WIFSIGNALED(status)` 分支）——test_package 的断言据此设计（多段链路、SIGABRT 触发重启），避免写出与上游语义不符的测试
- ✅ pipexec 以 `execv(params->path, …)` 按绝对路径拉起子进程（源码 `pipexec.c:250`）——测试必须自带 helper 子进程程序，无法依赖 shell 内建/`/bin` 工具

## 上游测试（R51 三步法）

### 第 1 步：清点

| 检查项 | 结果 |
|---|---|
| `tests/` 目录 | 不存在（测试在 `test/`） |
| `make check` 目标 | 形式存在但空（`Makefile.am`: `TESTS =` 无内容） |
| CTest / pytest 注册 | 0 |
| 上游测试入口 | 唯一：`test/basic_tests.sh`（35 行，4 项检查） |
| `test/ptest.c` | 只是示例用的 stdin/stdout 回环辅助程序（14 行），0 断言，不构成测试 |

`test/basic_tests.sh` 的 4 项检查：

| 用例 | 检查 | 断言 |
|---|---|---|
| T1 | 无参数运行必须失败（非 0） | 1 |
| T2 | 所有子进程成功 → 退出码 0 | 1 |
| T3 | 任一子进程失败 → 退出码非 0 | 1 |
| T4 | `'{ECHO:1>CAT:0}' '{CAT:1>GREP:0}'` 三段管道回传 `Hello World` | 1 |

### 第 2 步：实际执行

在本机（Ubuntu 24.04 容器，原生工具链，cwd = conan build 目录）真实执行：

```
TEST: run without any arguments
TEST: check return code when all childs succeed
TEST: check return code when one child fails
TEST: simple pipe
→ exit 0
```

**4 项全部通过，0 失败 0 跳过。** 运行前 `build()` 已按 `shutil.which()` 把脚本中的
`/bin/true|/bin/echo|/bin/cat|/bin/grep` 重定向为绝对路径（Linux 上本就存在，为 no-op；
OHOS 上映射到 `/system/bin/*` 等真实路径）。断言数量、顺序、判据均未改动。

### 第 3 步：回填

`test_package/MANIFEST.yml` 已记录：上游 4 项（`discovered/executed/passed = 4/4/4`）；
`build()` 输出 `HMBS_UPSTREAM_TEST_RESULT`（status=executed）。**真机复跑待执行**，
未写成 passed。

## 适配层补充测试（test_package，不替代上游统计）

标准三件套：`conanfile.py`（`can_run` 守卫 + CMake 构建 helper + OHOS 签名 staging）、
`CMakeLists.txt` + `pipehelper.c`（测试子进程程序）、`smoke.sh`（11 项断言）、`MANIFEST.yml`。

`smoke.sh` 11 项断言（本机实测 **11/11 通过**）：

| 用例 | 断言 | 实测 |
|---|---|---|
| T1 | `-h` 打印 `pipexec version 2.6.2` | PASS |
| T2 | 无参数 → exit 1 | PASS |
| T3 | 所有子进程成功 → exit 0 | PASS |
| T4 | 子进程失败 → 非零退出码 | PASS (rc=1) |
| T5 | fd 连线 `{ECHO:1>CAT:0}` 回传 `Hello World` | PASS |
| T6 | 三段链路 A->B->C（两条 pipe）4096 B 字节一致 | PASS |
| T7 | 65536 B 确定性负荷 produce\|consume 逐字节一致 | PASS |
| T8 | `-j` json 日志输出一个 JSON 对象 | PASS |
| T9 | `-p` 写出的 pidfile 内容 == pipexec 自身 pid（运行期观测） | PASS |
| T10 | `-s` 异常终止子进程被重启（SIGABRT 一次 → 两轮运行） | PASS |
| T11 | 子进程参数逐字透传 | PASS |

OHOS 细节：helper 是新链接的 ELF，在设备上需 `binary-sign-tool` 自签名且放到非 HMDFS 的
`/data/storage/el2/base/cache` 下才可执行（同 `archives/l/libxext/1.3.7`、
`archives/p/pipemeter/1.1.5`）。

## 验证结果

```text
# 本机（容器，原生工具链）
3 个补丁按 conandata 顺序 -p1 干净应用               PASS
config.guess (HarmonyOS uname) -> aarch64-unknown-linux-ohos   PASS
config.sub aarch64-linux-ohos  -> aarch64-unknown-linux-ohos   PASS
config.sub aarch64-linux-gnu 回归正常                PASS
外部 CFLAGS 保留于生成的 Makefile                    PASS
out-of-tree configure + make                        PASS
make check（上游 TESTS 空）                          PASS
make install -> bin/pipexec, bin/ptee, bin/peet      PASS
上游 test/basic_tests.sh                            4/4 PASS
test_package/smoke.sh（对**已安装**包内二进制）        11/11 PASS
package() 产物 = bin/{pipexec,ptee,peet} + licenses/LICENSE（ptest 已剔除）  PASS

# 用**真实 conanfile.py** 驱动 build()/package()/上游测试（stub conan，非手写复现）
_stabilize_autotools_timestamps() + configure + make + install + basic_tests.sh    PASS
_run_upstream_tests() /bin 重映射：PATH 无工具时回退 /system/bin 全部命中         PASS（单元测试）
_run_upstream_tests() 工具全缺时抛 ConanInvalidConfiguration（fail-closed）       PASS（负向测试）

# 仓库自带门禁（本地可跑部分）
ci/scripts/junk_check.sh（prdiff 模式）JC1–JC6      pass（单软件原子性合规）
ci/scripts/knowledge_check.sh KC1–KC5               pass
ci/scripts/preflight_check.sh pipexec/2.6.2         无依赖需检查（依赖为空）
L0h 裸用 ${CC}/${CFLAGS} 检测                       无命中
L0g 硬编码 remote 检测                              无命中

# OHOS 交叉编译探针
全部源文件 (clang --target=aarch64-linux-ohos -Werror -O3)   0 warning PASS
产物架构 = ELF64 / AArch64                           PASS
```

## 软件类型判定（R38）

产物为 3 个可执行文件，`package_info()` 显式清空 `libdirs`/`includedirs` → **CLI 工具**，
已在软件级目录补 `archives/p/pipexec/commands.json`（`type: tool`，
`versions["2.6.2"].ref: "pipexec/2.6.2"`，`binary: true`）。

## 注意事项

- `make install` 会装上游示例程序 `bin/ptest`，非运行时功能，已在 `package()` 中移除。
- **L2 冒烟门禁预期为 `warn`（非阻塞）**：CI 的 L2 用 `timeout 15 <bin> --version`，失败再试 `--help`。
  pipexec/ptee/peet 三个二进制的 `usage()` 一律以 `exit(1)` 结束（上游源码行为，`-h/--help/--version`
  实测 exit=1，`--version` 甚至报 `invalid option -- 'v'`），因此 L2 会打印
  `[warn] L2: <bin> --version/--help failed (non-blocking)`，`L2_RESULT` 保持 `warn`/`skip`。
  这是上游语义，**不通过改上游退出码去"骗绿"**；功能正确性由 test_package 的 11 项断言覆盖（其中
  T1 显式校验 `-h` 输出的版本串 `pipexec version 2.6.2`）。
- `pipexec -h` 走 `usage()` 且 `exit(1)`（不是 0），smoke T1 用 `|| true` 捕获输出后校验版本串。
- `pipexec` 2.6.2 禁止重复 pipe 端（`pipe_info_check_for_duplicates`：同一 from/to fd 只能出现一次），
  fan-in/fan-out 不可表达；且仅当子进程**异常终止**（信号/非正常退出）才重启（源码 `set_restart(1)`
  位于 `!WIFEXITED || WIFSIGNALED` 分支）。smoke 的 T6/T10 据此设计。
- 版本号与目录/引用一致：Conan 包版本 = 上游版本 = `2.6.2`（未发生制品仓版本冲突，无需递增后缀）。

## 会话决策记录

### 对话 #1 — 上游定位与归档选择
- `florath/pipexec` 404 → 经 GitHub 搜索定位到同名项目迁至 `flonatel/pipexec`，
  核实 tag/release/license 后采用。
- release asset vs tag archive：只有 release asset 含生成好的 autotools 文件，CI 镜像
  无 autoconf/automake，故选 release asset（并写入 manifest/README 说明原因）。

### 对话 #2 — 补丁 vs 配方内改
- E007（config.guess/sub）与 E165（/bin/sh）都是上游源码自身的可移植性缺口 → 落成
  portability 补丁，保持上游 `configure`/`make` 语义完整。
- CFLAGS 覆盖属配方能直接观察到的构建契约问题 → 同样落补丁（尊重用户 CFLAGS），
  而不是在 `generate()` 里用 `extra_cflags` 反复对冲。
- autotools 时间戳与上游测试的 `/bin/*` 路径属「配方侧运行环境」问题 → 在 `build()`
  内处理，不污染上游脚本。
- 上游测试没有因为「4 项很小」就跳过，真实执行并保留证据；未修改断言。

## 状态

- 状态：built
- 阻塞点：无（本机 B 阶段全通过）；待办：真机 shadow CI（单包排队）

---

## 下一步：真机 / shadow CI 命令（W5，本机无 conan 远端与真机窗口，未执行）

```powershell
# 0. 连通性（SSH 私钥路径/设备 IP/端口按本机实际替换，勿写入仓库）
ssh -i <private-key> -p <port> `
    -o StrictHostKeyChecking=accept-new -o IdentitiesOnly=yes `
    <user>@<device-ip> "echo ok"

# 1. 创建隔离 job（设备无 git 时用已有 repo 作 --repo-source）
sh "$HOME/bin/ohos-prepare-isolated-conan-job.sh" `
    --user codex --job pipexec-2.6.2-<timestamp> `
    --package archives/p/pipexec/2.6.2 `
    --repo-source "$HOME/ohos-users/codex/<existing-job>/repo/build_in_harmonyos"

# 2. 确认目标包目录齐全（conanfile.py / conandata.yml / patches / test_package / manifest / notes）
find archives/p/pipexec/2.6.2 -maxdepth 3 -type f | sort

# 3. 执行 runner
sh "$HOME/ohos-users/codex/<job>/run-conan-heavy.sh"

# 4. 读取结果：$HOME/ohos-test-runs/*pipexec*/logs/{exit-code.txt,stdout.log,stderr.log,runner.log}
#    重点核对：L0/L1/L2/L4/L5、上游测试 4/4、test_package 11/11
```

预期：`conan create` 走通，L0/L1/L4/L5 pass，L2 对 `bin/pipexec` 做 `--version/--help`
（`-h` 退出码 1，故以 `--help` 或版本串判定，非阻塞项），上游测试 4/4、test_package 11/11。
