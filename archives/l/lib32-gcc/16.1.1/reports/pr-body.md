- **三方库名称**：lib32-gcc
- **上游版本**：16.1.1（任务指定包版本名；实际源码为官方 GCC 16.1.0 发布 tarball——上游从未发布 16.1.1，仅存在 16.1.0/16.2.0，映射关系在 conandata.yml 头注与 notes.md 中如实记录）
- **上游仓库地址**：https://gcc.gnu.org/git/gcc.git （官方版本化发布档：https://gcc.gnu.org/pub/gcc/releases/gcc-16.1.0/gcc-16.1.0.tar.xz）
- **适配路径**：**路径 A（基础适配）＋ 路径 B（知识库扩展/贡献创新）＋ 路径 C（复杂工具链，候选）** 复合申报，最终认定权在评审委员会。**路径 A**：无 patches 目录，适配全部以构建期源码变换完成（config.gcc musl/ohos 分支放行 + `arm/linux-eabi.h` 后注入 `ohos.h`、config.sub 三元组放行、umask/HMDFS 变换），交付 C 交叉编译器 + 静态 libgcc + 包内 GNU ARM gas 的 conan 包（test_package 消费者端到端流程 2 用例 / 31 断言）。**路径 B**：知识草稿 `knowledge/drafts/DRAFT-lib32-gcc-16.1.1-ohos-arm-cross-toolchain.md/.kv`，沉淀 7 条可迁移条目（draft-review 预审最高相似度 0.14，无撞库），见下方「已沉淀的可复用知识」。**路径 C**：criterion 3/4 ＋ 难度兜底条款实证（8 轮平台 CI / 7 类平台死点），见下方「C 类候选依据」。
- **使用知识库**：同系先例知识草稿 DRAFT-gcc-snapshot-20260705-ohos-source-tree-and-fresh-build（GCC 自举工具链/HMDFS/spawn 管控），及仓内 HMDFS、ELF 签名、shell 入口等通用定律条目；本轮产出独立新草稿 1 份（draft-review 预审 create，最高相似度 0.14，无撞库）

## 测试用例对比

### 上游库测试用例统计

> 清点口径：**上游 N = 本配方所驱动套件的全家底**（不是本轮执行的子集）。
> 清点命令与读数：`find gcc/testsuite/gcc.c-torture/execute -name '*.c' | wc -l` → **1685**。

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 1685 | 来源：GCC 16.1.0 `gcc/testsuite/gcc.c-torture/execute` 全集 `.c` 源文件数（清点命令见上），即平台按源码清点得到的同一读数 |
| 集成测试 | 0 | 上游 GCC 无 conan test_package 形态 |
| 其他测试 | 0 | 完整 DejaGNU testsuite（`gcc/testsuite` 全量）未纳入本配方测试范围；`make -C gcc selftest` 虽在 `build()` 内以硬失败方式真实执行，但按「所驱动套件」口径不计入 N/N′（逐项说明见「未执行清单」） |
| **合计** | **1685** | 全家底清点口径；本轮实际执行 **100**（子集，逐项原因见下），未执行 **1585** 不宣称通过 |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试（torture 子集） | 100 | 执行 100 / 上游 1685（子集，原因见下节） | compile+link 口径：每例由构建树交叉驱动（xgcc + xgcc-sign wrapper → cc1 → 包内 GNU gas → collect2 → 设备 GNU ld 2.45 armelf_linux_eabi）编译+链接，`llvm-readelf -h` 校验产物为合法 ELF；aarch64 宿主不执行 ARM32 二进制 |
| 集成测试 | 0 | 不变 | 上游无此形态 |
| 鸿蒙特有测试（消费者用例） | 2 | 新增 | 用例①**完整消费者端到端流程**（预处理 → 编译 TU-A/TU-B → 汇编（包内 GNU ARM gas）→ 链接（设备 GNU ld）→ 产物校验，7 阶段）；用例②target ABI 程序（`-DEXPECT_OHOS=1`，编译期强制 `__OHOS__` + 32 位 ABI）。合计 **31 项硬断言**，明细见 `test_package/MANIFEST.yml` |
| **合计** | **102** | 执行 100 子集 + 新增 2 消费者用例 | |

### 上游测试用例执行范围与减少原因（N′ < N）

本轮执行 **100 / 1685**，未执行 **1585**。这不是「测试被删掉」，而是执行面受限于三项**具体技术原因**（未执行部分不宣称任何通过结论）：

1. **系统能力缺位（决定性）**：交叉产物是 32 位 ARM（`arm-linux-ohos`）二进制，构建宿主是 aarch64，**torture 程序根本无法执行**。已执行的 100 例采用明确的 **compile+link+ELF 校验口径**（编译+链接成功，产物经 `llvm-readelf -h` 判定为合法 ELF；ELF32/ARM 机型断言由 test_package 消费者流程强制），不混写为「执行通过」。
2. **驱动缺位**：上游完整的 DejaGNU torture driver 未移植为 OHOS runner。配方自带的是 bounded runner（逐源文件解析并遵循 `dg-additional-options`），可以批量驱动子集，但不是全量 driver 的等价替代——在把它移植完成前，剩余源文件没有可用的执行入口。
3. **构建窗口预算**：包级 CI 窗口（3600s，超时条目见下方说明）已被「配方自建 GNU ARM gas（binutils `all-gas`，CI 实测约 25 分钟）+ `all-gcc` + `all-target-libgcc`」占满（CI #50342 实证：3600s 恰好 KILL 在 libgcc 全量编译与安装完成之后，elapsedTime=3799s）。全量 1685 源（3370 个 compile+link 用例）不可能在本窗口内完成。

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例。torture 子集源文件按上游原样编译（仅解析并保留 `dg-additional-options`）；无 patches/ 目录，源码变换均为构建期脚本注入（config.gcc/config.sub/ohos.h，见 notes.md）。

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [x] **否**，上游已有测试用例覆盖（`gcc.c-torture/execute` 全家底 1685）。`test_package/` 是 Conan 包管理器要求的**消费者侧用例**（验证包安装后驱动链端到端可用），既不属于对上游测试的补全，也不并入上游分母；本轮按审查意见把它从「4 条孤立断言」改造为**一条完整的消费者端到端流程**（见下节）。

### 本轮新增的消费者用例（PC 消费者用例，对应「鸿蒙特有测试」行）

**用例①：消费者端到端流程**（全部由安装后的包驱动，`ignore_errors=False`，编译/链接非零退出直接失败）

| # | 阶段 | 动作 | 断言 |
|---|------|------|-----:|
| 1 | 驱动身份 | `gcc --version` | 1 |
| 2 | 目标身份 | `gcc -dumpmachine` == `arm-linux-ohos` | 1 |
| 3 | 预处理 | `gcc -E consumer_probe.c` → 预处理期即见 `__OHOS__`（`gcc/config/ohos.h` 注入生效，字面量 `arm-linux-ohos-32bit-abi` 出现在输出中） | 1 |
| 4 | 编译 TU-A | `gcc -O2 -c consumer_lib.c -o consumer_lib.o` → ELF32 / Machine ARM / Type REL、含 `.ARM.attributes`（包内 GNU ARM gas 指纹）、`consumer_compute` 为 DEFINED FUNC | 8 |
| 5 | 编译 TU-B | `gcc -O2 -c consumer_main.c -o consumer_main.o` → ELF32 / Machine ARM、`consumer_compute` 为 **UND**（跨 TU 依赖成立） | 5 |
| 6 | 链接 | `gcc -O2 consumer_main.o consumer_lib.o -o consumer_program`（collect2 → 设备 GNU ld） | 退出码 |
| 7 | 产物校验 | `llvm-readelf -h/-s consumer_program` → Type EXEC/DYN、入口地址非 0（`arm-linux-ohos` 启动文件链被链接进来）、`main` / `consumer_compute` / `consumer_target_abi` 均 DEFINED（跨 TU 符号在链接期被真正解析） | 12 |

**用例②：target ABI 程序** —— `gcc -O2 -DEXPECT_OHOS=1 test_gcc.c -o gcc_test_program`：`__OHOS__` 未定义或目标 ABI 非 32 位会让**编译本身失败**（`#error` / `_Static_assert`），随后校验产物为 ELF32/ARM。断言 3。

> 合计：**2 个消费者用例 / 31 项硬断言**。新增源文件：`consumer_lib.h`、`consumer_lib.c`（TU-A）、`consumer_main.c`（TU-B）、`consumer_probe.c`（预处理探针）。
> 为什么不做「执行产物」：交叉产物是 ARM32 二进制、宿主 aarch64 无法执行（与已合入的 `i686-elf-gcc/14.2.0`、`avr-gcc-bootstrap/14.2.0` 同类边界）。改用「跨 TU 符号在链接期被真正解析 + 启动文件链（入口地址非 0）+ 产物机型/汇编器指纹（`.ARM.attributes`）」作为端到端证据：这些性质空壳包无法伪造——CI L1e 破坏性校验（移走包内 `bin/`）后链接必然失败。

## 验证结果

- 编译状态：**通过** —— `conan create`（ci12，构建 + 上游测试 + package + test_package）exit 0；`conan-verify` 干净重建 G0/G1/G2/G3/G4 全 PASS；`finish` W3 本地 CI `L0_RESULT=pass` / `L1_RESULT=pass` / `L2_RESULT=pass`，构建汇总 `Success: 1, Pass rate: 100.0% (1/1)`
- 上游测试用例通过率：**100/100（100%）**（torture 子集，compile+link 口径；ci12 与 conan-verify 干净重建双次通过）；声明口径 **执行 100 / 上游全家底 1685**，未执行 1585 不宣称通过
- 新增测试用例通过率：**2/2 用例、31/31 断言（100%）**（test_package 消费者端到端流程）

## 未执行清单（边界如实声明）

- `make -C gcc selftest`：**已在 `build()` 内真实执行，并非未执行** —— `conanfile.py` 以硬失败方式调用该目标（非零退出即 `raise ConanException`，中止 `conan create`），ci12 与 conan-verify 干净重建均 exit 0，故判定通过。它按「所驱动套件」口径**不计入 N/N′**（N=1685 的口径是 `gcc.c-torture/execute`），因此不在本清单中。（平台 CI 第 6 败 #50342 因 3600s 时钟被 gas 自建挤爆，未跑到 selftest 阶段——这正是超时条目须走独立基础设施 PR 的原因，见 notes.md §17/§18.2。）
- 完整 DejaGNU testsuite：`gcc.c-torture/execute` 全家底 1685 个源文件中仅执行 50 个（× 2 优化档 = 100 例），未选源文件无通过结论
- 其他语言前端（C 仅）、bootstrap、LTO、multilib、共享库（`--disable-*` 显式关闭项）
- ARM32 产物在宿主上的执行（aarch64 宿主不具备 ARM32 执行能力，以 compile+link+readelf 作为替代验证口径）
- 制品仓 `conan upload`（软件级 `commands.json` 按 R38 写 `binary:false`）

## 补充说明

**关键适配点**（详见 notes.md 与知识草稿）：

1. **collect2 双重搜索劫持**：GCC configure 自动生成的构建树 `gcc/collect-ld`（shebang 脚本）在 collect2 的「名字外层 × COMPILER_PATH 前缀内层」搜索中跨前缀抢先命中，HMDFS 禁止不可信链 spawn 脚本 → torture 前幂等 unlink `collect-ld`/`real-ld`，让 collect2 落到设备 GNU ld 2.45（多目标含 `armelf_linux_eabi`）。
2. **交叉安装命名面**：交叉 GCC `make install` 只装前缀名（`arm-linux-ohos-gcc` ELF + 版本 symlink）；包内 wrapper 合成 `gcc`/前缀名/版本名/`cpp` 四名字，内部版本从 symlink 解析（不信任包版本号 16.1.1，真实内部版本 16.1.0）。
3. **目标工具分层（CI 自给自足）**：设备 GNU binutils 2.45 仅 AArch64 后端，且 OHOS spawn 管控禁止构建树 ELF execve 脚本与 RUNPATH 型 SDK 工具（PR CI #49850 即死于 libgcc configure 的 as 探测）——配方改为**自建 GNU ARM gas**：`conandata.yml` 声明 binutils-2.46.0 官方源，`build()` 在 GCC configure 前 `make all-gas`（`--target=arm-unknown-linux-ohos`、RUNPATH-free）装为 `target-tools/as`，包内交付为 `bin/as`；collect2 链接走设备 GNU ld（`armelf_linux_eabi`，系统分区）。gas 为设备本地验证过的同款构建（PR 不含二进制；缺失时硬失败）。
4. **ELF 签名硬要求**：未签名 driver 连 cc1 都无法 spawn；包内 host 可执行文件全部签名。

### 构建超时条目已拆分为独立基础设施 PR（与软件改动解耦）

本配方比同系先例（`gcc-snapshot/20260705`）多一段 CI 实测约 25 分钟的 gas 自建阶段，3600s 默认窗口不够（CI #50342 实证 elapsedTime=3799s 被 KILL）。该超时条目属于 `ci/config/build_timeouts.txt`（基础设施），按 `CONTRIBUTING.md` 协作者铁律「`ci/` 只读」与 `SKILL.md` §W2「框架改动必须单独提交 PR」，**已从本 PR 移除**，改以【基础设施】独立 PR 提交同一条目（内容见 `notes.md` §18.2）。本 PR 的 CI 需在该基础设施 PR 合入并 rebase 后复跑。

### 已沉淀的可复用知识

知识草稿 `knowledge/drafts/DRAFT-lib32-gcc-16.1.1-ohos-arm-cross-toolchain.md` 与对应 `.kv` 已沉淀可迁移条目（draft-review 预审 create，最高相似度 0.14，未与既有条目撞库）：

1. **collect2 的「名字×前缀」双重搜索与构建树劫持**：collect2 按「名字外层 × COMPILER_PATH 前缀内层」搜索 linker，configure 自动生成的构建树 `collect-ld` shebang 脚本会跨前缀抢先命中；修复二选一——unlink 让位设备 GNU ld（要求设备 ld 支持目标 emulation），或签名 ELF launcher 三别名（gcc-snapshot 路线）；只改 `-B` 顺序无效（名字外层循环仍先命中构建树脚本）。
2. **交叉 GCC 安装命名面**：`make install` 只装前缀名（ELF + 版本 symlink），无裸 `gcc`；包内 wrapper 需合成 `gcc`/前缀名/版本名/`cpp` 四名字，内部版本从版本 symlink 解析，不得用包版本号拼接 libdir。
3. **设备 binutils 与目标架构能力差的分层解法**：能力差是结构性的（GNU binutils 2.45 仅 AArch64 后端），且 OHOS spawn 管控使 SDK clang 无法充当构建树 xgcc 的目标汇编器（脚本/RUNPATH 型 execve 均被拒，PR CI #49850 实证）——唯一可行解是**配方自建 RUNPATH-free GNU gas**（conandata 声明 binutils-2.46.0 官方源，`make all-gas` 产物装为 `target-tools/as` 与包内 `bin/as`），链接走设备多目标 GNU ld。
4. **宿主不可执行目标产物时的 torture 验证口径**：口径 = 构建树交叉驱动 compile+link + `llvm-readelf -h` 合法 ELF 校验（机型断言在消费者测试强制），双次执行（初跑 + 干净重建）排除缓存；结论必须写明 compile+link 口径，不混写为「执行通过」。
5. **上游 N 的清点口径（本轮返修新增）**：上游「用例数」必须取**所驱动套件的全家底**（本包 `gcc.c-torture/execute` = 1685 源文件），配方实际执行的子集（100）只能作为 **N′** 单独申报并逐项写明未执行的具体技术原因；把 N′ 写成 N 会被判「少报」（rule4）。
6. **交叉工具链的消费者端到端用例形态（本轮返修新增）**：目标产物不可执行时，以「预处理 → 编译 2 个 TU（TU-B 只见声明，符号为 UND）→ 汇编 → 链接 → 产物校验（跨 TU 符号 DEFINED、入口地址非 0、机型与 `.ARM.attributes` 指纹）」构造完整消费者用例，替代孤立断言（rule12）。
7. **任务版本名与上游源码版本解耦的诚实记录**：16.1.1 任务名 vs 16.1.0 源码，映射以 conandata 头注 + 本地计算 sha256 + 与官方 sha512.sum 逐字节比对的交叉证据坐实；内部版本解析走真实来源。

与既有知识的关系：消费同系先例 DRAFT-gcc-snapshot-20260705 的 spawn 管控/ELF 签名定律；上述 ARM32 交叉特有指纹（设备 ld 多目标 emulation、前缀名命名面、跨架构能力差分层、宿主不可执行的验证口径与消费者用例形态、上游 N 全家底清点口径、版本名解耦）与 gcc-snapshot 的 AArch64 自举条目不撞库。

### C 类候选依据

本库 manifest 保留 `path_c_candidate` 标记（candidate 申报），最终等级以评审委员会结论为准。候选证据满足 criterion 3 与 criterion 4 两项：

1. **复杂工具链架构**（criterion 3）：GCC 含目标特定汇编器集成与生成式宿主工具架构；OHOS 构建需协同 host GNU as/ld（aarch64）、target ARM Clang/LLD（arm）、包内 GNU ARM gas、AArch64 PIE 链接、生成 ELF 签名、target sysroot 与编译器 `-B` 搜索顺序，并修复 collect2 跨前缀搜索劫持。
2. **高成本依赖与验证**（criterion 4）：bundled GMP/MPFR/MPC + 独立 flex/2.6.4 `tool_requires` + m4 与多个 GCC 生成器/runtime 组件；单次全量构建 2-3 小时，本轮完成初跑与干净重建两次全量验证（torture 100/100 + 消费者流程 2 用例/31 断言），超出默认交互窗口。
3. **难度兜底条款实证（多轮失败迭代 + 平台死点类别）**：平台 CI 共 8 轮（6 败 2 过；可定位编号 #49850、#50178、#50179、#50342 失败，#50379 与 rebase 后 #50506 通过，另有 2 轮失败未留可检索编号），叠加本地 ci3-ci12 十轮真机全量迭代；期间定位并闭环 **7 类平台死点**（notes.md §5/§9-§15/§17）：① 上游 config.gcc「Unsupported targets list」黑名单拦截 `arm-unknown-linux-ohos`（三元组不含 eabi 子串）；② 目标汇编器结构性缺位（设备 binutils 2.45 仅 AArch64 后端，xgcc 按 `-B` 搜索名为 `as` 的汇编器 → libgcc suffix 死点）；③ HMOS spawn 管控三定律（不可信链 spawn shebang=EACCES、RUNPATH ELF=静默 exit 1、用户区 symlink execve=EACCES、patchelf=EPERM）；④ HMDFS 对不可信进程的 symlink open() 拦截（libgcc soft-fp `Permission denied`）；⑤ collect2「名字×前缀」双重搜索被 in-tree `collect-ld` shebang 劫持（叠加自编 ld 缺 `armelf_linux_eabi` 仿真）；⑥ CI 基建三连（binutils 源站下载 93% 断流 IncompleteRead、HMDFS umask 0700 临时目录不可写、conan source() 访问 settings 禁令）；⑦ 3600s 构建时钟被 gas 自建 ~25min 挤爆（超时条目走独立基础设施 PR，见上）。另有 1 项配方工程缺陷（`_install_target_binary` str/Path 类型混用，§16）以入参类型级复刻测试收口——属代码缺陷，不计入平台死点。

边界：C 候选申报基于复杂工具链架构与验证成本，不基于闭源二进制或私有工具链；配方产品边界限定 C frontend、non-bootstrap、non-LTO、non-multilib，已在 manifest/notes 如实记录而非宣称完整 GCC 矩阵覆盖。

**如实记录的 L2 informational（门禁仍 PASS）**：`arm-linux-ohos-gcc-ar/-nm/-ranlib --version` 失败；核心驱动命令（gcc、前缀名、版本名、cpp、as、collect-ld、ld、real-ld、gcov*）全部 OK。

**版本与制品口径**：`gcc-16.1.0.tar.xz` SHA256 本地计算入 conandata.yml，SHA512 与官方 sha512.sum 逐字节一致；制品仓 upload 未执行 → 软件级 `commands.json` 按 R38 写 `binary:false`。

**质量门禁**：W4 Pre-PR 审计（含本轮返修复核）verdict=pass，P0=0、P1=0；软件级目录不新增 README.md/manifest.yaml（PF9 红线：PR 不得含版本目录层以上的软件级 README/manifest）。
