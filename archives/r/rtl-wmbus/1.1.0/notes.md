# rtl-wmbus 1.1.0 — HarmonyOS PC (OHOS aarch64) 适配笔记

- 三方库：rtl-wmbus 1.1.0
- 上游仓库：<https://github.com/wmbusmeters/rtl-wmbus>（tag `1.1.0` → commit `34684e655df70867ac86e799561ec6512c45be0a`）
- 源码来源：官方 GitHub tag 归档 `https://github.com/wmbusmeters/rtl-wmbus/archive/refs/tags/1.1.0.tar.gz`
  sha256 `0da72c7f5b026a4c0d8dc9beabba021f147c950f52eb8e09f4e41884d4f32ebf`
- 构建系统：纯 Makefile（单编译单元 `rtl_wmbus.c`，无 configure）
- 目标：`os=OHOS arch=armv8 compiler=clang compiler.version=15`
- 补丁：**0 个**（源码零改动，无任何平台宏）

---

## 1. W0 依赖发布检查（适配前第一件事）

上游 README 把 "RTL-SDR library" 列为依赖，但那是**运行时的对等进程**，不是链接期依赖：

```
rtl_sdr -f 868.95M -s 1600000 - 2>/dev/null | rtl_wmbus
```

`rtl_wmbus.c` 从 **stdin** 读取原始 IQ，只 `#include <complex.h> <math.h>` 等标准头；
Makefile 的链接行是 `... rtl_wmbus.c -lm`，**不含 `-lrtlsdr`**。

结论：配方 `requirements()` 为空，无 `requires`，因此不存在未发布依赖。
（附带核实：`conan download rtl-sdr/2.0.2 -r=ohpcd --only-recipe` 成功，R35 口径确认
RTL-SDR 本身已在制品仓发布；本次未使用。）

> 探测踩坑记录：制品仓对**不存在**的版本返回的不是 404，而是
> `ERROR: error:system acceleration policy not enabled. [Remote: ohpcd]`。
> 该报错是"未发布"的信号，不能误判为 registry 不可达。

## 2. W0b 历史经验与 CI 能力矩阵

- 本仓 `archives/r/rtl-wmbus/` 无历史归档（`git grep -l rtl-wmbus origin/main -- archives` 为空），
  属**首次适配**，无历史 notes.md 需要比对。
- 核验口径「历史命令在 CI clean 环境逐字可执行」：无历史，但已对照 CI 能力矩阵 —
  本包只需 `clang + make + C99`，属矩阵中 ✅ 项，不涉及 Rust/OCaml 等缺工具链分支。

## 3. 构建实现要点

### 3.1 版本横幅来自 git —— 需注入三个 Makefile 变量

上游 Makefile 的版本横幅来自 git：

```make
TAG?=$(shell git describe --tags --always)
BRANCH?=$(shell git rev-parse --abbrev-ref HEAD)
ifeq ($(BRANCH),master)
  BRANCH:=
else
  BRANCH:=$(BRANCH)_
endif
VERSION:=$(BRANCH)$(TAG)
```

Conan 的源码目录没有 `.git`，`git describe`/`rev-parse` 均失败：

- 什么都不注入 → `VERSION` 变成 `"_"`，横幅打印 `rtl_wmbus: _`，测试无法断言版本。
- 用 `make BRANCH=master TAG=1.1.0` 命令行注入 → 命令行赋值优先级高于 makefile 内赋值，
  `BRANCH:=` 的重写**失效**，横幅变成 `master1.1.0`（实测）。

**采用方案**：用 `GnuToolchain().extra_env.define()` 把 `BRANCH/TAG/COMMIT_HASH/CHANGES`
注入构建环境（conanbuild env 文件，`self.run()` 默认 source）。
GNU make 的优先级是「命令行 > makefile 赋值 > 环境变量」，环境变量只是默认值，
因此 `?=` 不会覆盖它们，而 `ifeq ($(BRANCH),master)` 仍会命中并清空 `BRANCH` ——
正好复现 tag 版 master 检出应有的横幅 `1.1.0`（实测 `-V` 输出 `rtl_wmbus: 1.1.0`）。

### 3.2 CC 必须走命令行

Makefile 里是 `CC=gcc`（普通赋值，不是 `?=`），会遮蔽环境里的 `CC`，
所以编译器路径必须显式覆盖在 make 命令行上，且按 R33 从
`self.conf.get("tools.build:compiler_executables")` 取，绝不裸用 `${CC}`。

### 3.3 平台适配：零改动

`rtl_wmbus.c` 自带 Windows/POSIX 分支（`WINDOWS_BUILD`），OHOS 走 POSIX 分支，
上游代码**一行不用改**：

| 上游能力 | OHOS 依赖 | 结论 |
|---|---|---|
| `signal.h` / `alarm()` / `sigaction` | musl | ✅ |
| `sys/socket.h` / `inet_aton` / `connect` | musl | ✅ |
| `<complex.h>` `cabs` / C99 复数 | clang C99 | ✅ |
| `-lm` | OHOS musl | ✅ |

编译告警仅 13 条且全部无害（clang 不识别 `-Waggregate-return`、`-Wcast-qual` 用于函数指针等
GCC 专有告警项，以及 `__attribute__((__packed__))` 位置告警），**0 error**。

按 R8，`patches/` 为空，未引入任何 `__OHOS__` 平台宏。

## 4. 上游测试清点与实测（R51 三步法）

### 4.1 清点：上游没有 `make check`

1.1.0 的 Makefile 目标只有 `all/release/debug/pi1/rebuild/install/clean`，**无 `make check`**。
上游的"测试"是 README 记录的**录波回放流程**：`samples/` 目录下有 4 个真实 RTL-SDR 录波，
把 cu8 原始 IQ 灌进解码器并核对输出报文。共 **4 个**用例。

### 4.2 实测：4/4 在 OHOS aarch64 产物上执行并通过

用本次 conan create 产出的 `rtl_wmbus`（OHOS aarch64，qemu-aarch64 执行）逐个回放：

| # | 上游录波 | README 建议参数 | 输出行数 | 模式 | 结论 |
|---|---|---|---|---|---|
| 1 | `rtlsdr_868.625M_2M4_issue48.cu8` | `-d 3 -s -o` | 2 | `T1` (CRC_OK) | ✅ |
| 2 | `rtlsdr_868.950M_1M6_issue47.cu8` | `-o` | 8 | `T1` + `C1` | ✅ |
| 3 | `rtlsdr_868.950M_1M6_issue49.cu8` | `-o` | 4 | `T1` | ✅ |
| 4 | `rtlsdr_868.950M_1M6_samples2.cu8` | 默认 | 4 | `T1`（含 `0;0` CRC 失败帧） | ✅ |

**N = 4（上游用例总数），M = 4（实测执行并通过）**，通过率 4/4 = 100%。

同时做了 OHOS vs 原生 x86(glibc) 的**逐字节交叉比对**：截断到足以锁定的前缀后，
OHOS aarch64 产物与原生 gcc 产物解码输出**完全一致**（地址/载荷逐字段相同），
说明交叉编译未改变 DSP 数值行为。

### 4.3 补全测试用例（CI 自动化部分）

CI 制品体积约束下，只有用例 1（README 原文用例、且体积最小）作为 fixture 随包提交：
- 原始 204800 B 的 `.cu8` **只提交 180224 B 前缀**——实测 176 KiB 解不出、180224 B 可解出，
  且截断前后解码输出逐字节相同；
- 因 R02（`git apply` 无法承载二进制补丁，"cannot apply binary patch ... without full
  index line"），原始二进制不能入库，改为 **base64(gzip()) 文本**，构建期由 CMake 用
  python3 标准库还原（与 `archives/l/libmysofa/1.3.5` 同一策略）；
- 生成脚本 `test_package/data/gen_fixture.py` 随包提交，可复现。

`test_package/` 共 **32 条断言**，其中鸿蒙特有测试 13 条（见 `ohos_special_test.c`）：

- ELF 层：`EM_AARCH64`、`ET_DYN`、`PT_GNU_STACK` 不可执行（NX）、`PT_INTERP` 指向
  `/lib/ld-linux-aarch64.so.1`（**仅作加载器路径/布局检查**：glibc 的 aarch64 加载器同名同路径，
  仅靠路径无法区分 musl/glibc）、`DT_NEEDED` **精确 soname** 比对无 `libc.so.6`/`libgcc_s.so.1`
  等 glibc soname 且含 musl 的 `libc.so`（这一条才是 musl/glibc 的真正判据）
- POSIX 层（上游 `WINDOWS_BUILD` 分支外才编译进来）：`-f` 流控在 stdin 停顿时由
  `alarm(5)+SIGALRM` 主动非零退出、`-p X` 非法模式被 getopt 拒绝、`-s` 组合模式可用

> 上述 OHOS 专属断言由 `test_package/conanfile.py` 依据 `settings.os`/`settings.arch` 下发的
> `TARGET_IS_OHOS_AARCH64` 门控（配方同时接受 `os=Linux`，此时这些 OHOS 期望不成立，
> 打印 `[skip]` 而非失败）。CI 恒为 `os=OHOS`/`arch=armv8`，13 条全部实跑。

## 5. 上游测试用例修改说明

**未修改任何上游测试**。上游没有测试框架/测试文件，本次也不改动 `rtl_wmbus.c`
或任何头文件，`patches/` 为空。

唯一与"上游用法"相关的一处观察（非本次修改项，供参考）：
`print_usage()` 宣称支持 `-h print this help`，但 getopt optstring 是
`"ofad:p:r:vVst:"`——**不含 `h`**，实际执行 `-h` 会报 `unrecognized option: h`。
这是上游 1.1.0 自身的缺陷。因此测试用 `-V`（真正实现）而非 `-h` 做版本/冒烟断言，
避免把上游缺陷写进断言。

## 6. 本地验证证据

```
conan create archives/r/rtl-wmbus/1.1.0 --name=rtl-wmbus --version=1.1.0 \
  -pr:h=ohos-aarch64-wsl -pr:b=ohos-aarch64-wsl --build=missing
→ exit 0
  test_decode          19 checks, 0 failure(s)
  ohos_special_test    13 checks, 0 failure(s)
```

同源 CI 门禁本地复跑（`CI_PACKAGES="archives/r/rtl-wmbus/1.1.0" zsh ci/conan/build_and_test.sh`）：

| 阶段 | 结果 |
|---|---|
| G0 知识图谱完整性 | pass |
| KC 知识质量 | pass |
| JC 杂项文件 | pass（涉及软件数 1，合规） |
| L0 质量门禁 (L0a–L0q) | pass |
| L1 测试执行 | pass（**L1e 破坏性反向验证通过**：移走 `bin/` 后测试确实失败，证明非空壳） |
| L2 冒烟 `--version/--help` | skip（非阻断，见下） |
| L4 补丁静态扫描 | pass（无补丁） |
| L5 产物基线 | pass（`bin/` 有内容） |

**L2 为何是 skip**：L2 依次尝试 `--version` 与 `--help`。rtl-wmbus 的 getopt optstring 是
`"ofad:p:r:vVst:"`，**不含长选项**，因此 `--version` / `--help` 都会被 getopt 当作无法识别的
长选项而报错并 `exit(1)`（同 5 节的 `-h` 问题）。这是上游 1.1.0 的既有行为，
L2 本身标注为 `[warn]` 非阻断，且本包已用真实可用的 `-V` 完成版本冒烟断言。

打包产物：`bin/rtl_wmbus`（ELF 64-bit LSB PIE, ARM aarch64, interpreter
`/lib/ld-linux-aarch64.so.1`, NEEDED `libc.so`）。

## 6.1 W4 Pre-PR 独立审计

用 `scripts/pre_pr_audit.py generate` 生成审计输入，派独立审计子任务按
`.gitcode/code-style.md` + `.gitcode/review-memory.md` 逐条核对，
结论 **verdict=pass，P0=0 / P1=0**。审计提出的 P2 已全部处理：

| P2 | 处理 |
|---|---|
| `ohos_special_test.c` 硬断言 `EM_AARCH64`/OHOS PT_INTERP，而 `validate()` 也接受 `os=Linux`，非 OHOS 构建会误判 | 期望值改由 `test_package/conanfile.py` 依据 `settings.os`/`settings.arch` 经 CMake 变量 `TARGET_IS_OHOS_AARCH64` 下发；非 OHOS 构建打印 `[skip]` 而非失败。CI 恒为 OHOS/armv8，全量断言照常执行 |
| musl soname 判定用 `strstr("libc.so")`，会误配 glibc 的 `libc.so.6`（断言近乎空转） | 改为 soname **精确比较**（`has_soname` / `is_glibc_soname` 白名单） |
| `CMakeLists.txt` 硬编码 `python3` | 改为 `find_package(Python3 COMPONENTS Interpreter)`，未找到时回退 `python3` |
| 13 个文件缺行尾换行 | 全部补齐 |

未采纳的两条 P2 及理由：

- **`url = ""  # CI fills this`**：这是仓库自身模板 `templates/conanfile-makefile.py.tmpl`
  与既有配方（如 `archives/a/aa3d/1.0`、`archives/a/a52dec/0.7.4`）的既定写法，非占位符违规。
- **未透传 toolchain 的 LDFLAGS/sysroot**：上游 Makefile 的链接行是硬编码的
  `... rtl_wmbus.c -lm`，不接受 `LDFLAGS`；本包只链接 `-lm`（无第三方库），
  实测 OHOS 链接与运行均正常，因此不打补丁改动上游构建逻辑（保持"零补丁"）。

## 6.2 建 PR 前置硬闸 PF9 的框架缺陷（非本包问题，供主编跟进）

`python3 scripts/ohc/preflight.py . origin/main HEAD` 对本包报出**且仅报出**一条：

```
PF9 分支/路径闸: 变更路径缺版本目录层（须 archives/<字母>/<包>/<版本>/<文件>）
  archives/r/rtl-wmbus/README.md, archives/r/rtl-wmbus/commands.json, archives/r/rtl-wmbus/manifest.yaml
```

PF9 判定条件是"所有 `archives/` 变更文件的路径段数 ≥ 5"，但：

1. `PF8`（R38/L0k）**要求** CLI 包必须有软件级 `archives/<字母>/<包>/commands.json`（4 段）；
2. `knowledge/ARCHIVE-SPEC.md` 规定 `README.md`、`manifest.yaml` 也是软件级；
3. CI 侧 `L0n` 只校验分支名，不校验路径深度；`L0k` 只校验 `commands.json` 内容。

即 PF9 与 PF8/ARCHIVE-SPEC/L0k 互相矛盾。已用**仓库内既有已合并配方**复现同一命中：
把 `archives/a/a52dec`（含软件级 `commands.json` / `README.md` / `manifest.yaml`）
的文件清单喂给 `preflight.check_branch_and_paths()`，得到**完全相同**的 PF9 命中 ——
证明这是框架侧误判，与本包无关。

处置：保留 `commands.json`（删掉它会直接触发 CI `L0k` 硬失败，比本地误判更糟），
建 PR 时使用框架自带的逃生口 `--no-preflight`，并在此记录证据。
按红线要求，本次**未修改任何框架文件**。

## 7. 过程中踩到的坑（已沉淀知识图谱）

1. **Conan 2.29 `GnuToolchain` 没有 `.vars`**：旧写法 `tc.vars["X"]="Y"` 报
   `AttributeError: 'GnuToolchain' object has no attribute 'vars'`；
   正确写法是 `tc.extra_env.define("X", "Y")`。
2. **本 OHOS 适配版 conan 的 `self.run(env=...)` 不是环境变量表**：它的 `env` 形参语义是
   "环境文件名列表"（默认 `conanbuild`/`conanrun`），传 dict 报
   `env argument to ConanFile.run() should be a list`，传 `[("K","V")]` 报
   `TypeError: expected str, bytes or os.PathLike object, not tuple`。
   传自定义环境变量要走 `GnuToolchain.extra_env`。
3. **`self.run()` 捕获子进程 stdout 后必须 NUL 结尾**：只 `out[0]='\0'` 不够，
   短输出会残留上一次更长输出的尾巴，导致行数/字段断言被污染（本包曾因此把
   2 行报文误判成 8 行）。
4. **`strncmp(ip, "/lib/ld-linux-", 15)` 恒不匹配**：字面量第 15 个字符就是 `'\0'`，
   与实际串的 `'a'` 冲突。应写成 `strncmp(..., 14)` 或用 `strstr` + 目录前缀判断。

## 8. 远端 CI 暴露的、本地无法复现的三个问题（PR #14175 实战记录）

本地 WSL 环境（qemu-aarch64 + /opt 交叉工具链）全绿，但远端 OHOS CI worker
（NDK 工具链 + 极简 PATH）连续三次红。三条都**不是配方逻辑问题**，而是
"本地工具链/环境的偶然行为被固化"或"操作流程"问题：

### 8.1 `fatal error: 'build/version.h' file not found`（第 1 次 CI）

上游 Makefile 在**解析期**用一串 `$(shell mkdir / echo / cat -n / mv)` 生成
`build/version.h`。CI worker 的极简 PATH（`/data/app/bin:/system/bin:...`）拿不到
这些调用所需的 coreutils——同一次日志里预下载步骤也是
`[Errno 2] No such file or directory`。于是 `cat -n` 两个探测都返回空，
`PREV_VERSION == CURR_VERSION`，Makefile 走 `rm` 分支，`version.h` **从未生成**。

> 本地复现：`make ... SHELL=/nonexistent/sh`（或使 `cat` 不可用）即可稳定复现。
> 注意 `$(info Building $(VERSION))` 仍会打印（`$(info)` 不经 shell），
> 所以日志里"Building 1.1.0"正常出现，极具迷惑性。

修法：`build()` 先按**与 Makefile 字节一致**（82 字节，已核对 sha256）的内容
自行写出 `build/version.h`。工具链正常时 Makefile 比较后同样走 `rm` 分支，
两种环境都成立。不改上游源码、不加补丁。

### 8.2 `PT_INTERP` 断言在远端红（第 2 次 CI）

```
[FAIL] PT_INTERP is the aarch64 loader under /lib (got "/lib/ld-musl-aarch64.so.1")
```

musl 动态加载器的文件名**不是唯一约定**：本地 /opt 工具链产出
`/lib/ld-linux-aarch64.so.1`，CI worker 的 NDK 驱动产出 `/lib/ld-musl-aarch64.so.1`。
断言写死单一拼写 = 把本地工具链的偶然行为固化成跨环境契约
（正是 W0b「历史/本地命令在 CI 是否逐字可执行」的反例）。

修法：改为语义匹配（`/lib/` 前缀 + `aarch64` + `ld-musl|ld-linux-aarch64`），
已对 6 个候选路径单测：两种 musl 拼写接受，glibc `/lib64/ld-linux-aarch64.so.1`、
`armhf`、bionic `linker64` 均拒绝。
**musl 与 glibc 的真正判别仍由 DT_NEEDED 精确 soname 比对承担**（OHOS 是 `libc.so`，
glibc 是 `libc.so.6`）——这条没有放宽。
同时把 `-f` 流控的时间上界从 8s 放宽到 30s：alarm 本身是 5s，本地实测 5~6s，
CI worker 负载高时多几秒属正常；该上界的作用是证明"进程会自行放弃而不是永久
阻塞在 read()"，不该成为红 CI 的原因。

### 8.3 PR diff 含二进制导致 `git apply` 失败（第 3 次 CI）

```
error: missing binary patch data for .../CMakeFiles/3.22.1/CMakeDetermineCompilerABI_C.bin
error: missing binary patch data for .../test_package/test_decode
error: PR 14175 diff 无法应用——PR 与 main 分支存在冲突
```

我在 `conan create` / 本地门禁复跑之后执行了 `git add -A archives/r/rtl-wmbus`，
把 CMake 产物（`CMakeFiles/**`，含两个真二进制）、已编译的 `test_decode` /
`ohos_special_test`、以及已解码的 180KB `issue48.cu8` 一并纳入了版本控制。
CI 以 patch 形式下发包，`git apply` 无法重建二进制补丁数据（R02）。

修法：新增一次清理提交把这些文件从 git 与工作树移除。归档树内现在只剩
15 个源文件 + W5 知识草稿，`junk_check` 通过，PR diff 全为文本。

> **流程教训**：适配期间每轮 `conan create` / 门禁复跑都会重新生成构建产物，
> 必须"先清理、再显式 `git add <具体路径>`"，**绝不能对包目录用 `git add -A`**。
> 这是本任务唯一一次违反红线的地方，已定位、已修复、已复验。
