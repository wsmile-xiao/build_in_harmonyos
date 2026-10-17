## PR 信息

- **三方库名称**：qbe
- **上游版本**：1.2
- **上游仓库地址**：https://c9x.me/compile/
- **适配路径**：路径 A（基础适配）+ 路径 B（贡献创新：1 条知识草稿，见下方「路径 B 知识贡献说明」）
- **使用知识库**：E002 / E052（`/tmp` 只读与临时目录，本 PR 补其"测试驱动硬编码"变体）、E063（clang 警告容忍）、E188（无 GNU install 的工具差异）、crasm 1.11 先例（Makefile CLI 配方骨架与 OHOS 签名处理）；本 PR 新增 `knowledge/drafts/DRAFT-9848-qbe-device-e2e-runtime-evidence`（路径 B 草稿）
- **任务号**：9848
- **分支**：feat/qbe-1.2

## 测试用例对比

### 上游库测试用例统计

| 测试类型 | 上游用例数 | 说明 |
|----------|-----------|------|
| 单元测试 | 0 | 上游无独立单元测试框架注册 |
| 集成测试 | 50 | `make check` = `tools/test.sh all`：对 `test/*.ssa` 逐项执行「qbe 生成汇编 → cc 链接（含用例内嵌 driver）→ 原生运行 → stdout/返回码比对」；`test/` 共 64 个 `.ssa`，14 个下划线前缀文件被上游 glob `[!_]*.ssa` 排除（上游设计，非裁剪） |
| 其他测试 | 0 | — |
| **合计** | **50** | 逐项清单与逐项运行模式见 `test_package/MANIFEST.yml` |

### 适配后测试用例统计

| 测试类型 | 适配后用例数 | 与上游对比 | 说明 |
|----------|-------------|-----------|------|
| 单元测试 | 0 | 不变 | — |
| 集成测试 | 50 | 不变 | 设备原生 arm64 路径实测：**49 PASS + 1 上游声明 SKIP**（dark.ssa 首行 `# skip arm64 arm64_apple rv64`）**+ 0 FAIL**；其中 13 项 stdout 比对、36 项返回码检查 |
| 鸿蒙特有测试 | 1 | 新增 | `test_package/test_qbe.sh`：以消费者身份执行打包后的 `qbe`（`-h`/`-t?` 目标自描述 + 两份最小 SSA 的「生成→链接→原生执行」+ 非法输入拒绝），12 项断言 |
| **合计** | **51** | **+1** | |

## 上游测试用例修改说明

### 是否存在对上游测试用例的修改？

- [x] **否**，未修改上游任何测试用例与断言；仅对测试驱动 `tools/test.sh` 做 1 行临时文件位置补丁（见下），断言逻辑未动
- [ ] **是**，存在对上游测试用例的修改（请在下方逐条说明）

> 补丁说明（`patches/0001-tools-test.sh.patch`）：
> - **修改的测试文件**：`tools/test.sh`（第 7 行）
> - **修改原因**：OHOS `/tmp` 只读，上游硬编码 `tmp=/tmp/qbe.zzzz` 使原样运行出现 `49 of 50 tests failed`（逐项报错 `cannot open '/tmp/qbe.zzzz.s'`），端到端验证在代码生成阶段即全部失败
> - **修改内容**：`tmp=/tmp/qbe.zzzz` → `tmp=${TMPDIR:-/tmp}/qbe.zzzz`（默认 `/tmp` 行为保持、不引入平台宏；配方在 `build()` 中传入 TMPDIR 指向 build 目录）

## 补全测试用例说明

### 上游是否存在无测试用例，适配后补全的情况？

- [ ] **否**，上游已有测试用例覆盖
- [x] **是**，适配后补全了 Conan 消费者测试

- **补全的测试范围**：`test_package/test_qbe.sh`——对「已打包产物」的消费者视角端到端验证（上游套件只运行源码树内构建的 qbe，不验证安装后的包）
- **补全原因**：需覆盖「打包链路完整性 + 默认目标自描述（`-t?`=arm64）+ 生成代码真实可执行（stdout/退出码）+ 非法输入拒绝」四类验收
- **新增测试文件清单**：
  1. `test_package/conanfile.py` — 测试入口（`VirtualRunEnv` + 绝对路径执行打包产物）
  2. `test_package/test_qbe.sh` — 12 项断言
  3. `test_package/MANIFEST.yml` — 上游测试逐项声明与断言计数

## 验证结果

- 编译状态：通过（`conan create` + `conan-verify` G0–G4 + 本地 CI 门禁，profile `ohos-aarch64-device`）
- 上游测试用例通过率：**49/49（100%，按可执行项）**；执行总数 50 = 49 PASS + 1 上游声明 SKIP（dark.ssa, arm64）+ 0 FAIL
- 新增测试用例通过率：**1/1（100%；12/12 断言）**

## 补充说明

### 构建环境与验证方式

- HarmonyOS PC 真机（aarch64），clang 15.0.4（OHOS SDK LLVM），Conan 2.29.1（OHOS 适配版）
- 构建：`make -j1 SHELL=sh CC=<conan-conf-c-compiler> CFLAGS="-std=c99 -O2 -g -Wall -Wextra -Wpedantic"`（编译器来自 `tools.build:compiler_executables`，R33）
- 上游套件：`tools/test.sh all`（=`make check`）在 `build()` 内、`can_run(self)` 时执行，`TMPDIR` 指向 build 目录（R51 层 1）
- `config.h` 由上游 Makefile 依 `uname -m` 生成：aarch64 → `#define Deftgt T_arm64`，设备原生即 arm64 目标（不启用交叉/qemu 分支）
- 消费者测试：`qbe -t?` 输出 arm64 → 两份最小 SSA（hello 输出比对 / 计算值退出码 42）→ 非法输入非零退出

### 配方要点

- **零依赖**：qbe 为自包含 C99 项目，无 Conan/runtime 依赖
- **补丁**：仅 `patches/0001-tools-test.sh.patch`（1 行；见上）
- **安装**：`package()` 复制 `bin/qbe` + `LICENSE` + `README`/`doc/*.txt`（设备无 GNU `install`，不使用上游 install 目标）
- **签名**：OHOS 下若 `/data/service/hnp/bin/binary-sign-tool` 存在则对包内二进制自签名（设备无该工具则跳过；与 crasm 先例一致）
- **commands.json**（R38，软件级）：`qbe`，type=tool，versions."1.2".ref=`qbe/1.2`

### 已知限制与未执行项

| 项 | 技术原因 |
|----|----------|
| amd64/rv64 后端运行验证 | 本平台（OHOS armv8）无对应目标执行环境；后端随源码编译通过，设备内验证范围以 arm64 为准 |
| `dark.ssa` | 上游首行声明 arm64 跳过（平台边界），非适配裁剪 |
| 14 个下划线前缀 `.ssa` | 不在上游 `make check` 的 glob 内（上游设计），不作为本包测试统计 |
| `qbe.ref` 汇编参考对照 | 上游源码包不携带该发布物，对照分支按上游逻辑自然跳过；汇编文本差异在上游也只是记录（`return 0`），行为验收以执行为准 |

## 路径 B 知识贡献说明

本 PR 按路径 A+B 申报，携带 1 条「一类问题」级知识草稿（与归档适配**同一 PR 原子交付**）：

- **新增草稿**：
  - `knowledge/drafts/DRAFT-9848-qbe-device-e2e-runtime-evidence.kv`
  - `knowledge/drafts/DRAFT-9848-qbe-device-e2e-runtime-evidence.md`
- **知识主题**：**编译器后端的设备内端到端运行证据链——测试驱动先失效（`/tmp` 硬编码）、环境契约与判定边界**。
  「自产代码执行型」编译器/代码生成/汇编器工具在 OHOS 设备内做验收时，必须建立
  `SSA → 汇编 → 设备内编译/链接 → 原生执行 → 行为比对` 的完整闭环，并显式声明执行分母、
  跳过归属与比对口径；**编译通过或汇编文本一致都不构成运行证据**。
- **触发实例（第一手，非转述）**：qbe 1.2 原样运行 `tools/test.sh all` → `49 of 50 tests failed`
  （逐项 `cannot open '/tmp/qbe.zzzz.s'`，失败发生在代码生成之前，"后端坏了"是伪象）；
  最小补丁 `tmp=${TMPDIR:-/tmp}/qbe.zzzz`（1 行、默认行为保持、无平台宏）后
  **49 PASS + 1 上游声明 SKIP（dark.ssa/arm64）+ 0 FAIL**，消费者 E2E 12/12。
- **查重结论与增量**（`draft-review` 预审结论：**create / 疑似新知**，最高相似 E356 score=0.19，
  远低于灰区阈值 0.30）：
  - **E002 / E052**：`/tmp` 只读事实层已覆盖——本条显式承认并超越：本变体是"驱动硬编码、环境变量不可覆盖"（必须最小补丁），
    且本条重心不在 `/tmp` 而在**证据链与判定边界**；
  - **E356**（chibicc 固定目标无运行证据 → 双平面）：**互补面**——E356 是"出不了运行证据"的一端，
    本条覆盖"能出运行证据"时的完整方法论（证据链构成/契约清单/计数口径/asm diff 非失败）；
  - **E387**（LLVM lit 框架配置与最小子集）：**分层不同**——本条为零框架、独立后端自带的最小 E2E 驱动，且以行为验收为准。
- **验证证据**：`reports/conan-create.log`（G2 干净构建内 `All is fine!` + 消费者 E2E 输出）、
  `reports/test-report.md`、`test_package/MANIFEST.yml`（50 项逐项声明）、设备侧 fail-first 与修复前后日志（仓库外留存）。
- **关联 Issue**：不适用（Issue 机制已废弃，按任务说明执行——同 ncmpc #9670 先例口径）。
- **分支**：`feat/qbe-1.2`；**任务号**：#9848。
