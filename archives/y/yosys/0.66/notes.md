# yosys 0.66 — 编译笔记

## 软件信息

- **名称**: yosys — Yosys Open SYnthesis Suite，开源 Verilog RTL 综合与形式验证框架
- **版本**: 0.66（GitHub tag v0.66）
- **许可证**: ISC
- **构建系统**: 自带 Makefile（既非 autotools 也非 cmake/meson）
- **目标平台**: OHOS aarch64（鸿蒙 PC）
- **上游**: https://github.com/YosysHQ/yosys
- **源码**: https://github.com/YosysHQ/yosys/archive/refs/tags/v0.66.tar.gz
- **sha256**: 096981d3cfd09a48cdd7cd52dd6135323477f9fb6b3bdcb09d4c7d8f1f324c99（3,633,415 字节）

## 编译环境

- 交叉编译（本地验证）: host = OHOS/armv8/clang15/libc++，build = 同 host（`ohos-aarch64-wsl-native`）
  - 说明: 制品仓的 abc/flex/bison 二进制按 OHOS/armv8 发布，`-pr:b=default` 会报 `Missing binary`；
    两者同 profile 也让 conan 认为非交叉、test_package 真正执行（本地由 binfmt_misc + qemu-aarch64 承担）。
  - 真实 CI 用 `ci/conan/profiles/ohos-aarch64`（native 鸿蒙电脑）。
- 编译器: `/home/qianxia/command-line-tools/sdk/default/openharmony/native/llvm/bin/aarch64-unknown-linux-ohos-clang(++)`
- 状态: built

## 编译步骤

1. `conan create archives/y/yosys/0.66 -pr:h=<profile> -pr:b=<profile> --build=missing`
2. `source()` 从官方 tag 归档解压（strip_root=True）
3. `generate()` 生成 VirtualBuildEnv / PkgConfigDeps，并把 tcl 的 `bin/` 与 tclsh shim 前置到 PATH
4. `build()`:
   - 从 conan `cxxopts` 包物化头文件到 `libs/cxxopts/include/`（上游子模块为空）
   - 以**环境前缀**注入 `CC`/`CXX`/`CXXFLAGS`/`LIBS`/`M4`/`BISON_PKGDATADIR`，执行
     `make -j<N> ENABLE_ABC=1 ABCEXTERNAL=<abc> DISABLE_SPAWN=0 TCL_VERSION=tcl8.6`（`N = min(tools.build:jobs 或 os.cpu_count(), 8)`，见问题 12）
5. `package()`: `make install PREFIX=<pkg> …` + 从 CC 同目录取 `llvm-strip`

## 遇到的问题与解决方案

| # | 首个错误原文 | 根因 | 修复 |
|---|---|---|---|
| 1 | `Missing binary: abc/0.0.0.20260511 … bison/3.8.2 … flex/2.6.4` | 这些是 tool_require（build 上下文），制品仓只有 OHOS/armv8 二进制，`-pr:b=default` 匹配不到 | 本地用 `ohos-aarch64-wsl-native` 同时作 host/build profile |
| 2 | `readline/readline.h: No such file or directory`（Makefile:794 driver.o） | 自带 Makefile 没有 pkg-config 分支，只有 `LIBS += -lreadline`，include/lib 需自己注入 | 注入 `CXXFLAGS`/`LIBS` **环境前缀**（`Makefile:107` 是 `CXXFLAGS := $(CXXFLAGS) -Wall … -I. …`，读环境值且保留 `-I.`；命令行赋值会覆盖并丢掉 `-I.`） |
| 3 | `bash: tclsh: command not found` | `Makefile:441` 硬编码调用 `tclsh`（`TCLSH=` 不被尊重），conan tcl 包只有 `tclsh8.6` | 在 generators 目录写 `tclsh` → `tclsh8.6` 的 shim 并前置 PATH |
| 4 | `bison: /share/bison/m4sugar/m4sugar.m4: cannot open` | conan bison 包把骨架放在 `<pkg>/share/bison`，未设 `BISON_PKGDATADIR` 时找 `/share/bison` | 传 `BISON_PKGDATADIR=<bison pkg>/share/bison` |
| 5 | `make: *** [frontends/verilog/Makefile.inc:9: …] Error 141`（真实信息 `bison: input/output error`） | 制品仓 bison 二进制**硬编码** `/data/service/hnp/bin/m4`（`strings <bison>/bin/bison` 实证），WSL 上该路径不存在 → bison 调 m4 失败 | 仅当 `/data/service/hnp/bin/m4` 不存在时注入 `M4=$(which m4)`；CI 上该路径存在，分支不触发 |
| 6 | `/usr/bin/ld: skipping incompatible …/libtcl8.6.so when searching for -ltcl8.6` | Makefile 自己给 `CXX`/`CC` 赋值（不是 `?=`），profile 的 `tools.build:compiler_executables` 到不了它 → 编出的是**宿主对象** | 在 `self.run` 的**环境前缀**里显式传 `CC=`/`CXX=`（与 `CXXFLAGS`/`LIBS` 同一方式；值取自 `self.conf`，R33） |
| 7 | `fatal error: 'FlexLexer.h' file not found` | flex 是 build 上下文 tool_require，其 include 目录未参与注入 | `_dep_flags()` 额外追加 flex 的 includedirs/libdirs |
| 8 | `ld.lld: undefined symbol: PC / BC / UP / tgetflag` | readline 的传递依赖 ncurses/tinfo 库未加入链接 | `_dep_flags()` 改为遍历**全部 host 依赖**（不再固定 5 个名字） |
| 9 | `make: *** [Makefile:856: check-git-abc] Error 1`（`… is not configured as a git repository, and 'abc' folder is missing`） | 上游 tag 归档的 `abc/` 子模块为空，`make install` 也会跑 `check-git-abc`，而 `ABCEXTERNAL` 只在 `build()` 传了 | `package()` 的 `make install` 同样传 `ABCEXTERNAL` 及完整环境前缀 |
| 10 | `strip: Unable to recognise the format of the input file '…/bin/yosys'` | `Makefile:126` 是 `STRIP ?= strip`，交叉编译时解析到**宿主** strip，读不了 aarch64 ELF | 从 C 编译器同目录取 `llvm-strip` 传 `STRIP=`（找不到时保持 Makefile 默认，native 构建不受影响） |
| 11 | 真机 CI（构建 #50968）：`sh: …/bin/yosys: Operation not permitted`（test_package 执行 `yosys -V` 失败） | OHOS 的 clang/lld 在**链接期自动自签** `.codesign` 段；`make install` 里的 `llvm-strip -S` 修改了 ELF 内容 → 签名失效 → 内核拒绝加载（EPERM，EXIT=126）。与权限无关（`chmod` 无效） | `package()` 在 `make install` 之后对 `bin/` 下每个 ELF（按 `\x7fELF` 魔数判断）走 E077 四步重签流程：`llvm-objcopy --remove-section .codesign` → `binary-sign-tool sign -selfSign 1` → `chmod 0755`；设备上生效，宿主交叉构建自动 no-op |
| 12 | 真机 CI（构建 #51146）：**构建超时**，`elapsedTime=3864s` > 默认 3600s 预算 | `make -j1` 串行编译 342 个目标，CI worker 实测 46~64 分钟（#50968 2785s、#51146 3864s），worker 速度波动大；而 `ci/config/build_timeouts.txt` 属框架文件（R21），不宜随包 PR 修改 | 改用并行构建 `make -j<N>`（`N = min(tools.build:jobs 或 cpu_count, 8)`，yosys Makefile 上游即以 `make -j$(nproc)` 构建），把构建压回默认预算内，从而**不动 `ci/`** |

### 本地调试时另遇到的两个**环境类**问题（非配方缺陷）

| 现象 | 根因 | 处理 |
|---|---|---|
| `Error loading shared library libc++_shared.so` / `libz.so` | 本机 LD_LIBRARY_PATH 未含 OHOS SDK 的 aarch64 运行库目录 | 本地验证时前置 `<sdk>/llvm/lib/aarch64-linux-ohos` 与 `<sdk>/sysroot/usr/lib/aarch64-linux-ohos`；设备/CI 由系统与 profile 提供 |
| `Error relocating …: __fd_chk: symbol not found` | 本机用的通用 Alpine musl loader 没有 OHOS musl 的 fortify 符号 `__fd_chk`（`sys/select.h:33` 声明 `void __fd_chk(int fd)`，`FD_SET` 宏调用它）；SDK sysroot 的 `libc.so` 只是 72KB 链接桩（所有 `_chk` 符号同址 0x11d80），不能当 loader | 本地编译一个 `void __fd_chk(int fd){(void)fd;}` 的 aarch64 共享库，用 `QEMU_SET_ENV=LD_PRELOAD=…`（只注入 guest，不污染宿主进程） |

## 源码修改

无。全部适配都在 `conanfile.py` 内完成：依赖注入、cxxopts 头文件物化、tclsh shim、
CC/CXX/STRIP/M4/BISON_PKGDATADIR 注入。未生成任何 `.patch`，未改上游源码。

## 依赖版本

| 依赖 | 版本 | 上下文 | 用途 |
|---|---|---|---|
| readline | 8.3 | host | 交互式命令行编辑 |
| libffi | 3.5.2 | host | TCL ffi |
| tcl | 8.6.16 | host | TCL 脚本绑定 / tclsh |
| zlib | 1.3.1 | host | 压缩输出（write_fst 等） |
| cxxopts | 3.3.1.1 | host | 命令行解析（头文件） |
| abc | 0.0.0.20260511 | host | 逻辑优化/工艺映射（运行时 exec） |
| flex | 2.6.4 | build | 词法分析器生成 |
| bison | 3.8.2 | build | 语法分析器生成 |

## 验证结果

### 1. conan create（真实通过）

- 命令：`conan create archives/y/yosys/0.66 -pr:h=<ohos-aarch64-wsl-native> -pr:b=<同名> --build=missing`
- 结果：`EXIT=0`；`yosys/0.66: Package 'c42828e97568cfa87dd952edd6ec0ca8338078f6' created`
- test_package **真实执行**安装后的 aarch64 yosys（经 binfmt_misc + qemu-aarch64）：
  - `PASS: yosys -V reports the 0.66 version banner`
  - `PASS: synthesized test.v (read_verilog + synth + stat)`（走通前端 → pass 管线 → techmap → 外部 abc）
- 日志：`/mnt/e/dsh working/tasks/yosys-0.66-2026-09-17/logs/033-local-create.log`（全量构建）、`034-local-create.log`（增量复验，6s）

### 2. conan-verify（全门禁通过）

- `python3 scripts/ohc-run.py conan-verify yosys 0.66` → **Verdict: PASS**
- G0 预构建风险评估 ✅ / G1 配方完整性 ✅ / G2 conan create ✅ / G3 系统同名库隔离(R26) ✅ / G4 产物完整性 ✅
- L2/L4/L5 在该报告里记为「跳过（无 cache 路径）」：G4 未能从 `@ohpcd/stable` 的 create 输出中解析出 package_id。
  这三项的实际执行见第 3 节 W3：L4（补丁扫描）=pass、L5（产物基线，bin/ 有内容）=pass；
  L2 对 `yosys` 二进制为 warn（直跑、未经 conanrun，`libtcl8.6.so` 不在 `LD_LIBRARY_PATH`），
  对 `yosys-config`/`yosys-smtbmc`/`yosys-witness` 为 ok，整体 L2=pass（非阻塞）
- 报告：`reports/conan-verify-report.md`；日志：`/mnt/e/dsh working/tasks/yosys-0.66-2026-09-17/logs/036-conan-verify.log`

### 3. W3 本地 CI 模拟（阻塞门禁，通过）

- `python3 scripts/ohc-run.py finish yosys 0.66 built` → `✅ 本地 CI 模拟通过`（`EXIT=0`）
- `.ci-result.json`（finish 生成）：`exit_code=0`、`integrity_hash=7f5e485f3b54ce34`、
  `log_sha256=5b7875c577671e7024f9048d7e0427895e0b2156424fccc5db6c995ebb9666a1`（与 `reports/w3-local-ci.log` 复算一致）
- W2 原子性（Step 9）：最终 PR 变更集为 **22 个文件**（`archives/y/yosys/**` 12 + `knowledge/drafts/**` 10），**无框架文件**
  （第一轮曾带入 `ci/config/build_timeouts.txt` 超时条目，审计 P2/R21 指出后已彻底移除；重提前已 rebase 到最新 upstream main）
- 说明：本机无 `/data/service/hnp`（鸿蒙设备路径），本地 W3 用 `ci/conan/profiles/ohos-aarch64`
  的 settings（os=OHOS/os.version=6.0/arch=armv8/clang15/libc++17/Release）不变、仅把
  `tools.build:compiler_executables` 指向本机 OHOS SDK 的 aarch64 clang（该行注释自述
  “工具链路径（环境特定，conan 无法自动探测）”）；实机 CI 用原始 profile。
- 日志：`/mnt/e/dsh working/tasks/yosys-0.66-2026-09-17/logs/039-finish.log`；`reports/w3-local-ci.log`

### 4. 上游测试（通道 B：aarch64-linux-ohos + qemu-user）

- 测试入口：`make -C tests vanilla-test`（`tests/gen_tests_makefile.py` 为各目录生成 Makefile，逐条调用 `$(YOSYS)`）
- 执行架构：**aarch64-linux-ohos**（仓库构建出的真实 yosys 二进制，经 `binfmt_misc` + `qemu-aarch64-static` 执行）
- 实测目录（32 个）：`arch/{analogdevices,anlogic,ecp5,efinix,fabulous,gatemate,gowin,ice40,intel_alm,machxo2,microchip,nanoxplore,nexus,quicklogic/pp3,quicklogic/qlf_k6n10f,xilinx}`、`arith_tree asicworld bind bugpoint hana opt rtlil sat sdc sim simple simple_abc9 svtypes techmap various verilog`
- **统计口径与结果（两个口径都给，差异逐条解释）**：
  - 以 `tests/**/*.result` 为准（`run_test` 宏逐用例写入 PASS/FAIL，是每用例的权威记录）：
    **本次执行到的用例数 N′ = 1005　通过 1002　失败 3　跳过 0（99.7%）**。
    N′ 只覆盖本次实跑的 32 个目录，**不等于上游套件总数 N**：`tests/unit`（需 `libyosys.so`）与其余约 22 个目录未运行。
  - 运行日志 `041-upstream-vanilla-test.log` 是**被中断的运行**（为把 CPU 让给 conan-verify 而 kill：含 7 处 `Terminated`、
    无 `VANILLA_RC`、末尾输出有丢失），日志中可数到的行为 **995 PASS / 5 FAIL / 28 个目录完成**。
  - **两个口径的差异逐条归因（已独立复核）**：
    - 总数差 1005 − 1000 = **5**：`tests/simple/{values.v, verilog_primitives.v, vloghammer.v, wandwor.v, wreduce.v}`
      这 5 条的 `.result` 为 PASS，但在被 kill 的日志里 **0 行输出**（缓冲丢失），故日志少数 5 条；
    - 失败数差 5 − 3 = **2**：`sdc/alu_sub.ys`、`sdc/side-effects.sh` 在日志中为 FAIL，补 `TCL_LIBRARY` 复跑后 `.result` 变为 PASS（复跑日志见下）。
  - 即：**以 `.result` 为准 1002/1005；以中断日志为准 995/1000**，两处差异均已定位到具体用例，无未解释差异。
- 失败与复跑逐条取证：
  - `sim/assume_x_first_step.ys`、`sim/vcd_var_reference_whitespace.ys` → `ERROR: Shell command failed!`（真实信息 `Exec: vcd2fst …`）：本机未安装 GTKWave 的 `vcd2fst`（`which vcd2fst` 为空）→ 环境缺失
  - `various/clk2fflogic_effects.sh` → `./clk2fflogic_effects.iv.out: cannot execute: required file not found`：本地 iverilog 为免 root 用户目录解包（`dpkg -x`），其生成物 shebang 为 `#! /usr/bin/vvp`，而 `/usr/bin/vvp` 不存在 → 环境缺失
  - `sdc/alu_sub.ys`、`sdc/side-effects.sh`：首轮 `ERROR: Tcl_Init() call failed - no such file or directory`；
    复跑日志 `042-upstream-sdc-retest.log` 同时记录了「不设 `TCL_LIBRARY` 时复现该错误（rc=1）」与「设 `TCL_LIBRARY=<tcl 包>/lib/tcl8.6` 后 `PASS alu_sub.ys` / `PASS side-effects.sh`」→ 环境变量缺失
- 未执行：`unit-test`（需先构建 `libyosys.so`，默认 `ENABLE_LIBYOSYS=0`）；其余约 22 个测试目录（`proc/fsm/memories/xprop/select/peepopt/aiger/…`）未运行（本地为让位 CPU 中断，未纳入统计）
- 日志：`logs/041-upstream-vanilla-test.log`（中断运行）、`logs/042-upstream-sdc-retest.log`（sdc 复跑取证）

### 5. test_package（消费者视角，单独一行）

- `PASS: yosys -V reports the 0.66 version banner`；`PASS: synthesized test.v (read_verilog + synth + stat)`


## 注意事项

- 上游 tag 归档 `v0.66.tar.gz` 的 `abc/` 与 `libs/cxxopts/` 是**空目录**（仅目录项、0 文件），不能树内构建。
  说明（避免失实）：官方 release 另有资产 `yosys-src.tar.gz`（11,178,019 B，2026-06-01）**内联**了 `abc/`（2316 文件）与 `libs/cxxopts`；
  本配方仍选择官方 tag 归档 + 制品仓的 `abc` / `cxxopts` conan 包（`abc` 已在制品仓发布且被其他配方使用）。
- `abc` 声明为 **host requirement** 而非 tool_require：yosys 在运行期 `exec()` 它，属于运行闭包；
  `package_info()` 用 `runenv_info.define("ABC", …)` 导出消费者自己的 abc 路径 ——
  `kernel/yosys.cc:652-657` 优先读 `getenv("ABC")`，否则会用到 `-DABCEXTERNAL` 固化的构建机缓存路径。
- `DISABLE_SPAWN=0` 是 `ABCEXTERNAL` 分支的**必需**项（`Makefile:493` 会 `$(error …)`）。
- 上游测试入口是 `make test`（= `vanilla-test` + `unit-test`），需要 `iverilog` 才能生成各目录的 Makefile。
---

**编译结束**: 2026-09-19 21:41
**最终状态**: built
