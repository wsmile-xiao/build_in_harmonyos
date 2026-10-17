# lib32-gcc 16.1.1 HarmonyOS PC 适配草稿（aarch64 宿主 → ARM32 交叉编译器）

- **草稿 ID**: DRAFT-lib32-gcc-16.1.1-ohos-arm-cross-toolchain
- **来源**: lib32-gcc/16.1.1 真机适配（ci10→ci12 三轮修复、conan-verify、finish W3 本地 CI）＋ 人工审查返修（rule4/rule5/rule12，2026-09-25）
- **分类**: toolchain / autotools / cross-compiler / ohos-platform / bundled-prerequisites / pr-review-compliance
- **状态**: 本地草稿（未创建 Issue/PR，未生成知识编号，无远端链接，无审核结论）
- **源码 URL**: `https://gcc.gnu.org/pub/gcc/releases/gcc-16.1.0/gcc-16.1.0.tar.xz`
- **源码语言**: C / C++
- **相关草稿**: DRAFT-gcc-snapshot-20260705-ohos-source-tree-and-fresh-build（同系 GCC 自举工具链，collect-ld 问题同象不同解，见「与既有知识的关系」）

## 范围

lib32-gcc 不是普通第三方库，而是**在 aarch64 HarmonyOS PC 宿主上自举、面向 32 位 ARM
（arm-linux-ohos）目标三元组发射代码**的交叉编译器包。它同时包含：

- 主体源码：`gcc-16.1.0.tar.xz`（任务指定包版本名 16.1.1，上游从未发布 16.1.1 tarball，
  仅存在 16.1.0 与 16.2.0；见 conandata.yml 头注与 notes.md）
- 内建前置：`gmp-6.3.0`、`mpfr-4.2.2`、`mpc-1.3.1`（与 16.1.0 的
  `contrib/download_prerequisites` 选择一致；isl/gettext 以 `--without-isl`/`--disable-nls` 关闭）
- 构建期生成器：`flex/2.6.4`（独立 `tool_requires`）
- 包内目标工具：GNU ARM gas（binutils 2.46.0 源码在 `build()` 期自建，OHOS 补丁内联应用）
  与设备 GNU ld 2.45 协同

适配重点不是"能否编过一个库"，而是：交叉驱动链在每个阶段（cc1 → gas → collect2 → ld）
都能被真实 spawn，且产物是合法的 32 位 ARM ELF。

## 关键现象

1. **ci10 torture 0/100**：collect2 的链接器解析是「名字外层（real-ld → collect-ld → ld）
   × COMPILER_PATH 前缀内层」的双重循环；GCC configure 会在构建树自动生成
   `<build>/gcc/collect-ld`（约 3.9KB 的 shebang 脚本），它**跨前缀抢先命中**，collect2
   对其 direct `posix_spawnp` 返回 Permission denied，100 个用例全军覆没。
2. **修复方向与 gcc-snapshot 不同**：本包不构造 signed ELF launcher，而是在 torture 前
   `unlink gcc/collect-ld` 与 `gcc/real-ld`，让 collect2 落到设备 GNU ld 2.45
   （`/data/service/hnp/bin/ld`，多目标构建含 `armelf_linux_eabi`）。幂等、OHOS-only。
3. **ci11 package 失败**：交叉 GCC `make install` 只安装前缀名（`arm-linux-ohos-gcc`
   为真实 ELF，`arm-linux-ohos-gcc-16.1.0` 为符号链接），**不存在裸 `gcc`**；消费方
   与 L2 门禁要求 `gcc`/`cpp`/版本名齐全 → 包内需合成 driver wrapper（4 名字），
   并**从版本 symlink 解析真实内部版本**，不得信任包版本号拼接 libdir。
4. **目标汇编器缺口（配方自给自足）**：设备 GNU binutils 2.45 只有 AArch64 后端、没有 ARM 后端；
   `hnp/bin/as` 不支持 `armv5t` 等老架构汇编；SDK clang 又不能充当构建树 xgcc 的目标汇编器
   （不可信链 spawn 脚本 = EACCES、RUNPATH ELF = 静默 exit 1，PR CI #49850 实证）。
   唯一可行解是**配方自建 RUNPATH-free GNU ARM gas**：`conandata.yml` 声明 binutils 2.46.0
   官方镜像回退源，`build()` 在 GCC configure 前 `make all-gas`（`--target=arm-unknown-linux-ohos`、
   `LDFLAGS=-static`），装为 `target-tools/as`（构建期）与 `bin/as`（包内、已签名）。
   **早期版本依赖外部环境变量 `OHC_ARM_GAS_BIN` 指定预编译 gas，已删除**——CI/本地同路径、
   包自给自足，消除"外部预编译工件依赖"审计项。
5. **交叉 torture 验证口径**：aarch64 宿主不能执行 ARM32 二进制 → 每个用例由构建树交叉
   驱动（xgcc + xgcc-sign wrapper → cc1 → 包内 gas → collect2 → 设备 ld）**编译+链接**为
   arm-linux-ohos ELF，再用 `llvm-readelf -h` 校验产物为合法 ELF（逐例校验的是"产生了
   合法 ELF"；ELF32/ARM 机型断言由 test_package 消费者流程强制），不执行。
6. **签名是硬要求**：未签名的 driver 连 cc1 都无法 spawn（`spawn: Permission denied`）；
   所有包内 host 可执行文件（driver、cpp、gas）必须 `binary-sign-tool` 签名。
7. **HMDFS 覆盖语义**：对已存在的大文件做覆盖写会失败（Operation not permitted），
   必须先 unlink 再写。
8. **版本口径的诚实记录**：`gcc-16.1.0.tar.xz` 的 SHA256 由本地计算写入 conandata.yml，
   且其 SHA512 与 gcc.gnu.org 官方 `sha512.sum` 逐字节一致（上游 16.1.0 只发布 sha512）。
9. **上游 N 的申报口径**（返修新增）：平台按**所驱动套件的全家底**清点（本包
   `gcc/testsuite/gcc.c-torture/execute` = **1685** 个 `.c` 源文件），把配方实际执行的子集
   （100）写成"上游用例数"会被判**少报**（rule4）。N 取全家底、N′ 单列执行数、未执行逐项列原因。
10. **鸿蒙特有测试的形态**（返修新增）：交叉工具链的目标产物在宿主上不可执行，
    孤立断言（`-dumpmachine`／退出码／readelf／静态断言）会被判"无完整消费者用例"（rule12）；
    需要构造**跨 TU 的完整流程**用例。

## 根因

- collect2 的双重搜索结构决定了：只修 `-B` 顺序或只提供 `ld` 别名都不够；构建树里
  configure 自动生成的 `collect-ld`/`real-ld` 是最高优先级命中点，要么替换为可 spawn
  的签名 ELF（gcc-snapshot 路线），要么直接移除让搜索落到设备工具链（本包路线）。
- 交叉 GCC 的安装布局以目标前缀为命名主体，裸名是宿主编译器（本包不交付）的约定；
  wrapper 必须补齐命名面而不是假装裸 `gcc` 存在。
- 宿主工具链（AArch64）与目标需求（ARM32）的 binutils 能力差是结构性的：目标 `as`
  不能靠宿主工具凑合，必须有真实的 GNU ARM gas 进入 `-B` 搜索路径。
- HarmonyOS 的 spawn 管控（不可信链 shebang EACCES、签名硬要求）叠加 HMDFS 覆盖语义，
  意味着"文件存在且 chmod +x"不等于"可被执行/可被覆盖"。
- 评审口径的两条结构性问题：**上游 N 的清点面是套件全家底而非执行子集**；
  **鸿蒙特有测试要求"完整消费者用例"而不是断言条数**。

## 已采用方案

- `_run_torture_execute_subset` 入口幂等 `unlink` `gcc/collect-ld`、`gcc/real-ld`
  （OHOS-only），torture 前 100/100 通过。
- `_install_ohos_driver_wrapper`：真身改名 `arm-linux-ohos-gcc-<ver>.real`，wrapper 以
  `/bin/sh` 入口合成 `gcc`/`arm-linux-ohos-gcc`/`arm-linux-ohos-gcc-<ver>`/`cpp`
  四名字，内部 `-dumpversion`/`-print-sysroot` 式解析（从版本 symlink 取真实版本）。
- `_build_target_gas`：`build()` 期从 `conandata.yml` 声明的 binutils 2.46.0 官方镜像
  回退源下载解包，套用 HMDFS umask 变换后 `make all-gas`，产物装为
  `target-tools/as`（构建期，`AS_FOR_TARGET`）并在 `package()` 期拷为 `bin/as` 后签名；
  缺失即硬失败，不静默降级。
- source 支持 `GCC_SNAPSHOT_SOURCE_TARBALL` 本地源包回退（真机开发通道；
  CI 正常路径走官方 URL + SHA256 校验，该变量仅限本地开发）。
- driver/cpp/gas 全部签名；HMDFS 覆盖一律 unlink-then-write。
- `test_package` **消费者端到端流程**（8 阶段 / 31 断言 / 2 用例，详见 §可迁移知识条目 7）：
  预处理 → 编译 TU-A → 编译 TU-B → 汇编（包内 GNU ARM gas）→ 链接（设备 GNU ld）→
  产物校验（ELF32/ARM、Type、入口地址非 0、跨 TU 符号 DEFINED、`.ARM.attributes` 指纹），
  外加 `-DEXPECT_OHOS=1` 的编译期 `__OHOS__` + 32 位 ABI 断言程序。

## 验证状态

- `conan create`（ci12 全量：构建 + 上游测试 + package + test_package）：exit 0。
- torture 子集 100/100（ci12 与 conan-verify 的 W3 干净重建**双次**通过）；
  **申报口径：N（上游全家底）= 1685，N′（实际执行）= 100，未执行 1585 不宣称通过**
  （清点命令 `find gcc/testsuite/gcc.c-torture/execute -name '*.c' | wc -l`）。
- `conan-verify lib32-gcc 16.1.1`：G0/G1/G2（干净重建）/G3/G4 全 PASS。
- finish W3 本地 CI：L0/L1/L2 均 pass，构建汇总 `Success: 1, Pass rate: 100.0% (1/1)`。
- test_package：**2 个消费者用例 / 31 项硬断言**（返修前为 4 条孤立断言，被 rule12 判不通过）。
- 返修期本机复检（宿主 `clang 15.0.4` 原样跑通流程编排，仅替换驱动身份并放宽三元组断言）：
  31 项断言全部真实执行，其中 10 项失败且**全部为 OHOS 专有项**（ELF32/ARM 类与机型、
  `.ARM.attributes`、GCC 16.1 版本身份），机械部分全绿；`test_gcc.c` 的
  `_Static_assert(sizeof(void *) == 4)` 在 64 位宿主上真实失败，证明该 ABI 断言有效。
- 如实记录的 L2 informational（门禁仍 PASS）：`arm-linux-ohos-gcc-ar/-nm/-ranlib
  --version` 失败；核心驱动命令（gcc、前缀名、版本名、cpp、as、collect-ld、ld、
  real-ld、gcov*）全部 OK。
- 制品仓 upload 未执行 → `commands.json` 按 R38 写为软件级 `binary:false`。

## 可复用结论

- 适合所有"aarch64 宿主 + ARM32/其他 32 位目标"的交叉工具链包。
- 适合记录 collect2 双重搜索结构的两类修复（unlink vs signed launcher）及其适用分野。
- 适合记录交叉安装只装前缀名、wrapper 需合成命名面并从 symlink 解析内部版本的包。
- 适合记录宿主/目标 binutils 后端能力差、目标汇编器必须随包交付的场景。
- 适合记录宿主不可执行目标产物时，torture 用 compile+link+readelf 作为验证口径的场景，
  以及**上游 N 必须按套件全家底清点**、未执行逐项列技术原因的申报范式。
- 适合记录"目标产物不可执行"类交叉工具链的**消费者端到端用例构造范式**（跨 TU + 链接期
  符号解析 + 启动文件链 + 机型/汇编器指纹），以替代被判定为无效的孤立断言。

## 可迁移知识条目

### 1. collect2 的「名字×前缀」搜索与构建树 collect-ld 劫持

- **触发条件**：交叉 GCC 链接阶段报 `collect2: fatal error: posix_spawnp:
  Permission denied`，而设备 `ld` smoke test 单独执行正常。
- **根因**：collect2 按 real-ld → collect-ld → ld 的名字顺序 × COMPILER_PATH 前缀
  顺序搜索；configure 自动生成的 `<build>/gcc/collect-ld` shebang 脚本跨前缀抢先命中，
  HMDFS 不允许不可信链 direct spawn shebang 脚本。
- **诊断方式**：`collect2 -debug` 查看最终 `ld_file_name`；确认命中的是构建树脚本
  还是受保护 HNP 工具。
- **处理方式**：两条路线二选一——(a) torture/build 前 unlink `gcc/collect-ld`、
  `gcc/real-ld`，让搜索落到设备 GNU ld（要求设备 ld 支持目标 emulation，如
  `armelf_linux_eabi`）；(b) 构造真实签名 ELF launcher 并同时提供
  `ld`/`collect-ld`/`real-ld` 三别名（gcc-snapshot 路线，适合设备 ld 不可用场景）。
- **验证方式**：torture 子集整批跑；单跑 `collect-ld --version` 不足以证明链接路径。
- **不要这样做**：不要只改 `-B` 顺序——名字外层循环仍会先命中构建树脚本。

### 2. 交叉 GCC 安装只装前缀名，wrapper 需从 symlink 解析内部版本

- **触发条件**：package 阶段或 L2 门禁报"找不到 gcc"；或 wrapper 拼接的
  `-B<pkg>/lib/gcc/<target>/<ver>` 目录不存在。
- **根因**：`make install`（交叉配置）只安装 `arm-linux-ohos-gcc`（ELF）与
  `arm-linux-ohos-gcc-<真实版本>`（symlink）；包版本名（16.1.1）≠ 内部版本（16.1.0）。
- **处理方式**：真身改名 `.real`，用 `/bin/sh` 入口 wrapper 合成
  `gcc`/前缀名/版本名/`cpp` 命名面；内部版本从版本 symlink 读取，不信任包版本号。
- **验证方式**：逐一执行四个名字的 `--version` 与 `-dumpmachine`；用消费者测试
  真实编译一个程序。
- **不要这样做**：不要用包版本号拼接 libdir，也不要把裸 `gcc` 做成指向宿主编译器的
  symlink 来"满足"门禁。

### 3. 宿主/目标 binutils 后端能力差必须用配方自建目标 gas 补齐

- **触发条件**：消费者编译报 `Error: unknown pseudo-op` 或 `armv5t` 等架构不被支持；
  设备 `as --version` 显示仅 AArch64 后端；SDK clang 作为目标汇编器被 spawn 管控拒绝。
- **根因**：设备 GNU binutils 2.45 多目标构建不含 ARM 后端；宿主 `as` 无法服务
  ARM32 目标汇编；clang 路线在不可信链下被 spawn 三定律阻断（PR CI #49850）。
- **处理方式**：配方声明 binutils 官方镜像回退源，在 `build()` 期自建
  `--target=arm-unknown-linux-ohos` 的 RUNPATH-free `gas`（`make all-gas` + `LDFLAGS=-static`），
  装为构建期 `target-tools/as` 与包内 `bin/as` 并签名；wrapper 的 `-B` 顺序把包内 `bin`
  与 target-tools 放在设备工具目录之前；缺失时硬失败。
  **不要引入"外部预编译 gas 环境变量"**——那会让 CI 与本地走不同分支，且构成外部工件依赖。
- **验证方式**：`p/bin/as --version` 显示 ARM 支持；用含 `armv5t` 指令的汇编源实测；
  `llvm-readelf -h` 校验产物 ELF32/ARM。
- **不要这样做**：不要把目标汇编静默降级到 clang 集成汇编器后仍宣称交付 GNU 工具链语义。

### 4. 宿主不可执行目标产物时的 torture 验证口径与上游 N 清点

- **触发条件**：aarch64 宿主 + ARM32 目标，torture 用例无法在宿主执行。
- **根因**：交叉编译器只保证"能生成正确目标代码"，执行验证需要目标运行环境。
- **处理方式**：每例由构建树交叉驱动编译+链接；`llvm-readelf -h` 校验产物为合法 ELF
  （ELF32/ARM 机型断言在消费者测试强制）；测试结论写"compile+link 100/100"，不写
  "执行通过"。
- **同时必须做对的清点口径**：上游"用例数"取**所驱动套件的全家底**（本例
  `gcc.c-torture/execute` = 1685 个 `.c` 源文件，清点命令 `find ... -name '*.c' | wc -l`），
  配方实际执行的子集（100）作为 **N′** 单独申报，并对未执行部分**逐项列具体技术原因**
  （系统能力/驱动缺位/窗口预算），不宣称通过。把 N′ 写成 N 会被判**少报**。
- **验证方式**：ci12 与 conan-verify 干净重建双次执行，排除一次性缓存命中。
- **不要这样做**：不要把宿主 qemu 方案未验证的"可执行"写进结论，也不要把编译通过
  混写为"测试通过率 100%"而不注明口径，更不要把执行子集当作上游总数申报。

### 5. 任务版本名与上游源码版本解耦的诚实记录

- **触发条件**：任务指定包版本名（16.1.1）在上游没有对应发布物（仅 16.1.0/16.2.0）。
- **根因**：任务平台的版本号不可改；诚实做法是记录映射而不是伪造 16.1.1 存在。
- **处理方式**：conandata.yml 头注 + notes.md 写明版本名与源码版本的关系；sha256
  本地计算入库，SHA512 与官方 `sha512.sum` 逐字节比对作为交叉证据；内部版本解析
  全部走真实来源（symlink/dumpversion）。
- **验证方式**：审计方可用官方 sha512.sum 独立复核。
- **不要这样做**：不要在正文或 manifest 里声称源码为 16.1.1。

### 6. 构建超时条目属于基础设施，不能随软件 PR 提交

- **触发条件**：包级构建超出 CI 默认 3600s 窗口（本包因配方自建 gas 约 25min 而超时，
  CI #50342 elapsedTime=3799s 被 KILL）。
- **根因**：`ci/config/build_timeouts.txt` 是基础设施配置（协作者铁律列 `ci/` 为只读；
  SKILL §W2 要求框架改动单独提 PR）。把它带进软件 PR 会被 rule5
  （"存在非 archives/knowledge 目录的文件改动"）判 FAIL——**与条目内容是否正确无关**。
- **处理方式**：软件 PR 只含 `archives/` 与 `knowledge/` 改动；超时条目走独立的
  【基础设施】PR，合入 main 后 rebase 软件分支再触发 CI。落地顺序不可颠倒：
  否则软件 PR 会持续红在 3600s 超时上（表面像配方问题，实为基建未落地）。
- **验证方式**：`ohc-run.py timeout get lib32-gcc 16.1.1` 返回 7200；CI 日志出现
  `Extended build timeout for lib32-gcc/16.1.1: 7200s`。
- **不要这样做**：不要为了绕过 rule5 而把超时写进配方（配方无法改动 CI 时钟），
  也不要删掉 torture/测试来"挤进"窗口。

### 7. 交叉工具链的消费者端到端用例构造范式（替代孤立断言）

- **触发条件**：鸿蒙特有测试行只有孤立断言（`-dumpmachine`／编译退出码／readelf 机型／
  编译期静态断言），被 rule12 判"纯断言、无完整消费者用例"。
- **根因**：断言检查的是"某条命令的单个输出"，不构成"跑通一条真实功能/流程"；
  而交叉工具链的目标产物（ARM32）在 aarch64 宿主上不可执行，容易被误认为"只能断言"。
- **处理方式**：构造**跨 TU 的完整流程**，所有阶段由**安装后的包**驱动：
  ① 驱动身份（`--version`）② 目标身份（`-dumpmachine`）③ **预处理**（`-E`，验证
  `__OHOS__` 已在预处理期生效）④ 编译 TU-A（函数定义，校验 `DEFINED FUNC` +
  `.ARM.attributes` 汇编器指纹 + `Type REL`）⑤ 编译 TU-B（只见声明，校验符号为 **`UND`**）
  ⑥ **链接**两个 TU ⑦ 产物校验（`Type EXEC/DYN`、**入口地址非 0**（启动文件链已链接）、
  `main`/跨 TU 符号 `DEFINED`）⑧ 编译期 ABI 程序（`#error`/`_Static_assert` 让错误目标
  直接编译失败）。
- **为什么这构成端到端证据**：跨 TU 符号只有在**链接期**被真正解析才为 `DEFINED`；
  入口地址非 0 证明目标启动文件被找到并链接；`.ARM.attributes` 是包内 GNU ARM gas 的
  产物指纹。空壳包无法伪造这三件事——移走包内 `bin/`（CI L1e 破坏性校验）后链接必然失败。
- **验证方式**：宿主工具链可先做一遍"机械复检"（替换驱动身份、放宽三元组断言），
  确认流程编排、参数顺序与断言解析逻辑正确，OHOS 专有项留待真机/CI 复验。
- **不要这样做**：不要只增加断言条数而不引入跨 TU/链接阶段；也不要在宿主上"假装执行"
  目标产物（qemu 未验证时不得写入结论）。

## 与既有知识的关系

- **同象不同解**：collect-ld 问题与 DRAFT-gcc-snapshot-20260705 相同象（collect2 命中
  构建树脚本、HMDFS spawn 管控），但解法分野——gcc-snapshot 用签名 ELF launcher
  三别名，本包用 unlink 让位设备 ld。两条路线的适用条件（设备 ld 是否支持目标
  emulation）是本草稿的增量。
- **复用不重复**：spawn 管控定律（不可信链 shebang EACCES、签名硬要求）、HMDFS
  unlink-then-write、CONFIG_SHELL/ulimit 等通用定律已在知识库既有条目中，本草稿只
  引用不展开。
- **返修新增条目的定位**：条目 4 的上游 N 清点口径与条目 7 的消费者用例范式属于
  **评审门禁口径类**知识（rule4/rule12），与既有 E544（rule12 行不得为 0）、
  DRAFT-E596（同 tarball 子包按父 tarball 全量注册面清点）、DRAFT-E2175（静态库包的
  产物级消费者验证）互补：本条给出**交叉工具链**（目标产物不可执行）场景下的具体形态。
- **去重说明**：error_signature 刻意以 ARM32 特有指纹为主
  （arm-linux-ohos-gcc / armv5t / gcc-16.1.0.tar.xz / ELF32 / collect-ld），
  避免用泛化症状与 gcc-snapshot 条目撞库。

## 路径 B/C 候选边界

- 路径 B 候选（知识库扩展）：本草稿即申报材料，共 **7 条**可迁移条目；
  **候选状态，最终认定权在评审委员会**。
- 路径 C 候选：交叉自举工具链（bundled GMP/MPFR/MPC + 独立 flex + 目标汇编器协调 +
  全链签名），高成本验证；同样为候选申报，不做自称。
