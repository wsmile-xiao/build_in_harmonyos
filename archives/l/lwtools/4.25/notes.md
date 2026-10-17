# lwtools 4.25 适配笔记

## 编译环境

- 目标平台：HarmonyOS PC（HAD-W32 / aarch64 / HongMeng 1.12），Conan profile `ohos-aarch64-device`
- 编译器：Harmonybrew `ohos-sdk@26.0.0.18/native/llvm/bin/clang`（15.0.4），`ar`/`ranlib` 走 `$HOME/work/shared/bin`（R33：Conan conf 优先，显式回落 `llvm-ar`/`llvm-ranlib`）
- 构建系统：上游自带**纯 POSIX Makefile**，无 configure / autotools / cmake，无第三方依赖
- 包管理：OHOS 适配版 Conan 2.29.1；本地源码树 `tmp/builds/lwtools-4.25.{orig,work}`（`.orig` 保持未修改原样）
- shell 环境为 toybox + ash，调试脚本注意：`grep` 不支持 BRE 的 `\|`（需 `-E`）、无 `cat -A`、`$(( ))` 内不能嵌套 `$( )`、`/tmp` 只读（`TMPDIR` 需指向 `$HOME/work/kasumizawa-miyuu/tmp`）

## 编译步骤

```bash
# 模式 B：先探索式编译，再落到 conan 配方
make -j1 CC=<clang> AR=<ar> RANLIB=<ranlib> PREFIX=<pkg> all   # MAIN+SECONDARY 共 7 个程序
make test                                                       # perl test/runtests → opcodes6809.pl

# conan 配方验证
python3 scripts/ohc-run.py conan-verify lwtools 4.25 --profile ohos-aarch64-device
#   build(): make -j1 ... all + 真实执行 perl test/runtests（272 断言，任何失败即中止）
#   test_package: sh test_lwtools.sh → 20/20 断言通过（真实执行已安装二进制）
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `lwcc -E` / `lwcc -c` 对**任何**输入文件都 SIGSEGV（rc=139） | `lwcc/cpp-main.c` 只创建了 5 个全局字符串列表中的 4 个，漏掉 `sysmacrolist`；`process_file()` 无条件调用 `lw_stringlist_reset(NULL)` → 写 NULL。与平台无关 | 上游缺陷补丁 `patches/0001-lwcc-cpp-main.c.patch`（+2 行：创建 + 销毁）。必要性实测（设备循环计数，未归档，见下文「补丁必要性与崩溃率」）：**未打补丁 10/10 次崩溃**，打补丁后同一输入 0/30 次失败 |
| 2 | 上游自带测试只覆盖 `lwasm`，`lwcc` 的必崩缺陷因此随 4.25 一起发布 | `test/tests/` 仅有 `opcodes6809.pl` | 交付时同时跑上游 272 断言 + 我们自写的 `test_lwtools.sh` 20 断言（后者覆盖全部 7 个程序的真实调用） |
| 3 | HMDFS 下 `lwcc` 找不到子组件而回退到 PATH | HMDFS 不上报可执行位，驱动里的 `access(X_OK)` 恒为假（`lwcc/README.txt` 亦说明依赖 PATH 回落） | 测试脚本显式传 `-B<pkg>` 且 `export PATH=$pkg/bin:$PATH`；`package_info()` 用 `runenv_info.prepend_path("PATH", …)`，`package()` 逐个 `chmod 0755` |
| 4 | 驱动内嵌 `BASEDIR` 与实际安装布局不一致 | 驱动默认在 `$(PREFIX)/lib/lwcc/` 找组件，`PREFIX` 编译期固定 | `make` 传入 `PREFIX=<package_folder>`，与 `install-all` 布局一致（`bin/` + `lib/lwcc/bin/`） |
| 5 | `make install` 不可用 | CI worker 无 `install(1)` | `package()` 直接复制并校验产物存在（缺失即 `ConanException`） |
| 6 | `lwcc-cpp` 宏展开阶段**偶发** SIGSEGV（未修复，见「注意事项」） | 上游实验组件缺陷 | 不把该不确定性写进断言；用无宏输入保证 test_package 可重复 |

## 源码修改

- 仅 1 个上游缺陷补丁：`patches/0001-lwcc-cpp-main.c.patch`（+2 / -0）
  - 由 `python3 scripts/ohc-run.py refresh-patch --auto lwtools 4.25` 生成，未手写
  - 分类：`upstream-bugfix`，`platform_only: false`，`guard: none`（无条件生效，因为该缺陷在所有平台一致）
  - `conandata.yml` 的 `patch_type` 有意写作 `bugfix` 而非代码规范示例中的 `portability`：本补丁修复的是上游与平台无关的逻辑缺陷（`platform_only: false`），标为 portability 会与事实相反；仓库自身的配方生成器 `scripts/ohc/conan_recipe.py:311` 同样会对上游缺陷产出 `bugfix`
  - 补丁内容不含 `__OHOS__` / `/usr/local` / `SYS_PREFIX`（PF5/PF6 自查通过）
- `.orig` 与 `.work` 树哈希由 `manifest.yaml` 的 `patch_generation` 记录，可复核

## 依赖版本

**W0 依赖检查结论：无第三方依赖，`requires` 为空，无需从制品仓拉取任何包。** 证据（均为工具产出，非推断）：

```
# 上游构建系统里没有任何外部库链接声明
grep -nE "^[[:space:]]*(LDLIBS|LIBS|LDFLAGS)[[:space:]]*=" Makefile */Makefile   →  无输出

# 实际产物的动态依赖只有 libc（设备上的 `llvm-readelf -d | grep NEEDED` 即时输出，未随包存档）
lwasm -> libc.so     lwlink -> libc.so     lwar -> libc.so     lwobjdump -> libc.so
lwcc -> libc.so      lwcc-cpp -> libc.so   lwcc-cc -> libc.so

# 配方侧
grep -c "def requirements" conanfile.py  →  0     （纯 ISO C + POSIX，仅需 libc）
```

构建期工具：`make` / `clang` / `ar` / `ranlib` / `perl`（上游测试驱动为 perl 编写，OHOS 构建环境提供）。运行期无额外依赖。

## 验证结果

### 有归档日志支撑的数字

以下每一条都给出**日志文件与行号**，可逐行复核。主证据日志是 finish step[5/10] 产出的 `reports/w3-local-ci.log`（521 行）。工具写入的 `archives/l/lwtools/4.25/.ci-result.json` 记录了该日志的 `log_sha256`（`integrity_hash` 亦由工具生成，不可手工伪造），复核时对同一文件执行 `sha256sum reports/w3-local-ci.log` 应与之逐字符相等；本文不复制哈希字面量，以免因重新构建而失真。

| 验证项 | 结果 | 证据位置（`reports/w3-local-ci.log`） |
|--------|------|----------------------------------------|
| 干净构建（非缓存命中） | `RUN: make -j1 CC=… AR=… RANLIB=… PREFIX=… all` 真实执行 | :188 |
| 上游套件逐字输出 | `opcodes6809 : 272/272 (0 skipped, 0 unknown, 0 failed)` / `Total: 272/272 (…)` | :420、:422（配方把 `upstream-tests.log` 回显进构建日志） |
| 上游套件解析结果 | `lwtools upstream suite: 272/272 opcode assertions passed (skipped=0 unknown=0 failed=0)` | :423 |
| 打包产物计数 | `package(): Packaged 11 files`（仅计数，日志不枚举文件名） | :429 |
| test_package | `1..20` + `lwtools test_package: 20/20 assertions passed, 0 failed` | :483、:484 |
| 破坏性负测 L1e | 移走 `bin/` 与 `lib/` 后测试确实失败 → 断言真实依赖被测包 | :495-497 |
| 门禁汇总 | `L0/L1/L2/L4/L5_RESULT=pass`、`JC: no junk files detected`、`Success: 1 Failed: 0`、`Pass rate: 100.0% (1/1)` | :507-511、:89-91、:517-519 |

`reports/conan-create.log`（406 行）是 `conan-verify`（设备 profile）那次干净构建的完整输出，独立给出同一组结论：:109 真实 `RUN: make -j1 …`（用的是本机 Harmonybrew OHOS SDK clang）、:341 与 :343 上游逐字 `opcodes6809 : 272/272` 与 `Total: 272/272 (0 skipped, 0 unknown, 0 failed)`、:344 解析汇总、:350 `package(): Packaged 11 files`、:383 test_package 以 `sh "<script>"` 调用、:404-405 `1..20` / `20/20`。两份日志（`w3-local-ci.log` 与 `conan-create.log`）来自两次独立执行，互不引用。

### 其余检查项的准确状态（不夸大）

- `conan-verify`（归档件 `reports/conan-verify-report.md`，43 行，Profile `ohos-aarch64-device`，Verdict PASS）：G0 :8、G1 :12、G2 :26、G3 :30、G4 :33 均为 ✅ PASS（其中 G0 :9-10 只记录了「构建系统: unknown，跳过预查询」，对本纯 Makefile 工程没有实际断言）。但 G4 同段自报"⚠️ 无法找到程序包 ID"，其后的 L2/L4/L5 标记为"⏭️ 跳过（无 cache 路径）"，即这三项在该步**没有实际执行**。因此产物完整性与冒烟测试的**有效证据来自 `w3-local-ci.log`**（:429 打包文件计数、:509 七个程序的 `--version` 冒烟、:511 `bin/` 有内容），而不是这些跳过项。
- **设备与 CI worker 的 profile 差异**：`finish` step[4/10] 内部调用 `conan-verify` 时不带 `--profile`，会回落到仓库自带的 CI worker profile 文件 `ci/conan/profiles/ohos-aarch64`，其中 `tools.build:compiler_executables` 指向 worker 路径 `/data/service/hnp/bin/clang`。该路径在本设备不存在，故一旦被其他参与者清掉 conan 缓存，这一步会以 `make: /data/service/hnp/bin/clang: No such file or directory`（`Error 127`、`Error in build() method, line 136`）失败——本轮流程中确实出现过一次（finish 运行日志，未随包归档；当时的 `conan-verify-report.md` 也因此短暂为 FAIL，现归档件是改用设备 profile 重跑后的结果）。这是**环境差异，不是配方缺陷**：设备侧必须显式 `--profile ohos-aarch64-device`（Harmonybrew OHOS SDK clang），阻塞门禁 W3 也始终用设备 profile。真实 CI runner 上 worker profile 路径成立。
- finish step[3/10] 的 "G0 干净构建验证" 报 `configure 失败 (exit 127)`：该步骤硬编码 `./configure`，只适用于 autotools 工程；lwtools 是纯 Makefile 项目，无 configure 脚本，此为工具侧的适用范围问题，**非构建失败**（真正的干净构建见 :188）。
- CI L2 冒烟对 7 个程序逐个跑 `--version`，`lwobjdump` 该项失败为**非阻塞告警**（:509）：上游 `lwobjdump` 本就无 `--version`/`--help`，非适配引入。其功能由断言 7（安装）与断言 11（对真实目标文件回读 `SECTION mytext` 与机器码）覆盖。
- CI L1c（:490）提示"日志中无 make check/ctest"：上游驱动是 `perl test/runtests` 且把结果写文件，故 L1c 的正则识别不到；配方已改为把该日志的尾部若干行（含 `Total:` 汇总，见 :420-422）回显进构建日志，并自行解析、非全通过即中止构建（`conanfile.py` 的 `Total:` 正则 + `ConanException`）。

### test_package 的 20 条断言

6 个二进制的 `--version` 横幅（`lwasm`/`lwlink`/`lwar`/`lwcc`/`lwcc-cpp`/`lwcc-cc`）、`lwobjdump` 已安装、`lwasm --raw` 金样字节流 `8e400034108612a70035101f8912`、`lwasm --obj` 产物、`lwlink --raw` 金样 `8e40008612a70012`、`lwobjdump` 反汇编回读（段名 + 机器码）、`lwlink -m` map 文件、`lwar` 建包/列表/逐字节解包（3 条）、非法操作码非零退出、缺文件报错信息、`lwcc-cpp -o` 直调预处理（补丁回归）、`lwcc -B<pkg> -E` 走驱动预处理、`lib/lwcc/bin/lwcc-cpp` 可直接执行（驱动组件布局）。每条断言在**所有分支上都恰好计数一次**（前置条件失败会记为 `NOT OK`，不会伪装成跳过）。

注：L1e 的破坏性负测同时移走 `bin/` 与 `lib/`，因此它不能单独区分二者；`lib/lwcc/bin` 的布局由断言 20 独立覆盖。

### 补丁必要性与崩溃率（设备上的循环实测，非归档日志）

下表数字来自在设备上运行的独立计数循环（每次 10~80 次调用，逐个记 rc），**未随包存档**，不属于上面"有日志支撑"的部分；其作用是说明补丁为何必需、以及为何断言不使用宏输入。所用二进制即 :188 那次构建的产物。

| 场景 | 失败次数 | 说明 |
|------|----------|------|
| 未打补丁，无宏输入，直调 `lwcc-cpp -o` | 10/10 | 全部 rc=139（SIGSEGV）→ 补丁为**必需**而非可选 |
| 已打补丁，无宏输入，直调 `lwcc-cpp -o` | 0/30 | 断言 18 采用的形态 |
| 已打补丁，无宏输入，经驱动 `lwcc -E` | 0/30 | 断言 19 采用的形态 |
| 已打补丁，对象宏 `#define ONE 1` **被使用**，直调 `-o` | 17/40；另一次 26/60（rc=0→34，SIGSEGV→26，其它 0） | 残留上游缺陷，见「注意事项」 |
| 同上，直调且输出走 stdout | 12/40 | 与输出目标无关 |
| 同上，仅 `#define` 不使用 | 0/40 | 触发点在宏**使用**，不在宏定义 |
| 同上，完全无宏 | 0/40 | 正常路径 |
| 同上，经驱动 `lwcc -E` | 0/80 | 两轮各 40 次未复现 |
| 已打补丁套件连续独立运行（`sh test_lwtools.sh`） | 3 次均 20/20 | 归档日志中另有 :484 的一次 20/20 |

失败输出特征：崩溃总是留下**空**输出文件；成功运行的输出字节一致（60 次运行仅 1 个非空摘要，115 字节）→ 不会静默产出错误结果。



## 交付物

| 文件 | 说明 |
|------|------|
| `conanfile.py` | Conan 2 配方（application，纯 Makefile 驱动；`build()` 内真实执行上游 272 断言） |
| `conandata.yml` | 官方 https 源码地址（R39）+ sha256 + 补丁系列 |
| `patches/0001-lwcc-cpp-main.c.patch` | 唯一上游缺陷补丁（`refresh-patch --auto` 生成） |
| `test_package/{conanfile.py,test_lwtools.sh,MANIFEST.yml}` | 20 条功能断言 + R51 测试清单 |
| `manifest.yaml` | 构建元数据、sha256、补丁生成与分类记录 |
| `notes.md` | 本文件 |
| `../commands.json`、`../README.md`、`../manifest.yaml` | 软件级 CLI 声明（R38）与中文说明 |

产物布局由 `conanfile.py` 的 `PROGRAM_DIRS`/`DRIVER_COMPONENTS` 与 `package()` 决定（:429 只给出 11 这一计数，文件名不在日志中）：`bin/{lwasm,lwlink,lwar,lwobjdump,lwcc,lwcc-cpp,lwcc-cc}` + `lib/lwcc/bin/{lwcc-cpp,lwcc-cc}`（驱动运行期组件）+ `licenses/{COPYING,GPL3}`（随包附带上游 GPL-3.0 正文）。

## 注意事项

- **`lwcc` 是上游标注为 experimental 的组件**，且上游自身在 `lwcc/README.txt` 中声明"预处理器/编译器直接接口刻意不定义，依赖预处理器输出格式是被明确禁止的"。因此本包只按驱动行为验收，不对其内部直调接口作稳定性承诺。
- **残留上游缺陷（未修复，如实记录）**：`lwcc-cpp` 在**使用**对象宏时仍会以约 30%~43% 的概率 SIGSEGV（`-o` 形态 17/40 与 26/60；输出走 stdout 时 12/40）。已排除的方向：与堆校验工具无关（ASan 在本内核无法产出报告）、与 ASLR 无关（关闭随机化仍崩）、与输出目标无关（`-o`/stdout 均复现）。崩溃**总是**留下空输出文件、成功输出字节一致（60 次运行仅 1 个非空摘要），因此不会静默产出错误结果。经 `lwcc` 驱动 80 次运行未复现。该缺陷跨平台同源（纯 C 逻辑），不属于本包适配范围，未一并打补丁，留待后续单独修复。
- `lwcc-cpp` 的第二位置参数形式（`lwcc-cpp in.c out.i`）在**正常**情况下即以 rc=255 报错（把第二个参数当作又一个输入文件），不作为崩溃率统计口径。
- 上游测试驱动 `test/runtests` 依赖 `perl`；若 CI worker 无 perl 需按 R51 说明原因，而不是跳过该套件。
- 产物为可执行命令集，已在软件级 `archives/l/lwtools/commands.json` 声明（R38）。
- `reports/` 下的日志与测试报告均不入库，只有审计产物 `reports/audit-result.json`（由 `scripts/pre_pr_audit.py` 生成）随 PR 提交：`test-report.md`、`conan-create.log`、`w3-local-ci.log` 属构建过程证据，按仓库评审规则 #19（禁止在 PR 中携带 `*.log` 与测试报告类文件）与 `knowledge/ARCHIVE-SPEC.md` 对 `packaging/`、`.staging-verified` 的废弃声明，保留在本地工作目录不随 PR 提交；本文「验证结果」小节已给出这些日志内的行号，评审需要原文时可随时提供。
---

**编译结束**: 2026-09-19 21:20
**最终状态**: built
