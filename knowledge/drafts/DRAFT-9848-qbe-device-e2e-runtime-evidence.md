# DRAFT: 编译器后端的设备内端到端运行证据链——测试驱动先失效、环境契约与判定边界（qbe 1.2 实例）

- **草稿 ID**: DRAFT-9848-qbe-device-e2e-runtime-evidence
- **关联 PR**: #10377（`feat/qbe-1.2`，路径 A+B 原子交付）
- **来源库**: qbe 1.2（SSA → amd64/arm64/rv64 汇编的编译器后端；MIT；纯 POSIX Makefile）
- **环境**: OHOS PC aarch64（HongMeng Kernel 1.12.0），clang 15.0.4（OHOS SDK LLVM），Conan 2.29.1（OHOS 适配版），toybox 用户态
- **状态**: 草稿（待主编 promote 为正式 E 条目；引用条目 E002/E052/E356/E387 为边界对照组）

## 1. 触发实例：失败先发生在测试驱动（真机实测）

qbe 的验收本质是"让它生成的 arm64 代码真的跑起来"。未打补丁、原样在设备运行上游驱动：

```sh
$ sh tools/test.sh all
abi1.ssa...    cannot open '/tmp/qbe.zzzz.s'
[qbe fail]
...
49 of 50 tests failed!
```

**故障不在后端**：49 个用例连汇编都没来得及生成，就被临时文件路径挡住了——
现象像"arm64 后端坏了"，实际是证据链断在测试驱动的宿主机假设上。

最小补丁（1 行，`patches/0001-tools-test.sh.patch`，默认行为保持、无平台宏）：

```diff
--- a/tools/test.sh
+++ b/tools/test.sh
@@ -4,7 +4,7 @@
 bin=$dir/../qbe
 binref=$dir/../qbe.ref
 
-tmp=/tmp/qbe.zzzz
+tmp=${TMPDIR:-/tmp}/qbe.zzzz
```

同一环境、配方以 `TMPDIR=<build>/qbe-test-tmp` 驱动：

```sh
$ TMPDIR=<build>/qbe-test-tmp CC=<clang> sh tools/test.sh all
...
All is fine!     # 49 [ok] + 1 上游声明 skip（dark.ssa）+ 0 fail
```

正式 `conan create`（conan-verify G2）内复验：`All is fine!`；随后消费者 E2E：

```
qbe consumer E2E passed: target=arm64 hello='hello from qbe' exit=42
```

## 2. 根因：环境契约与判定边界都属于"证据链"的一部分

### 2.1 驱动层的宿主机假设（本次真凶）

| 驱动行为 | 设备现实 | 配方必须补的契约 |
|----------|----------|------------------|
| `tools/test.sh:7` 硬编码 `tmp=/tmp/qbe.zzzz` | OHOS `/tmp` 只读（E002 同族），环境变量 TMPDIR 不可覆盖 | 最小补丁 `${TMPDIR:-/tmp}`；配方把 TMPDIR 指向 build 目录 |
| `cc="${CC:-cc}"` | 干净 PATH 下 `cc` 不可依赖 | 显式传 `CC=<conan conf c compiler>`（R33） |
| `TARGET=`$bin -t?`` 自描述目标 | aarch64 → `config.h` 由 `uname -m` 生成 `#define Deftgt T_arm64` | 原生路径即 arm64，**不得**启用交叉/qemu 分支 |
| 用例内嵌 `# >>> driver`（awk 抽取） | 无 | driver + 生成的 `.s` 一起交给 cc（嵌套编译） |
| 链接串 `-lpthread` | OHOS clang 15.0.4 可直接链接（实测 49 项无链接错误） | 无需替换 |
| `#!/bin/sh` 与 make 的默认 SHELL | 设备有 `/bin/sh`，CI worker 不保证 | `make SHELL=sh`、以 `sh tools/test.sh all` 显式调用 |

### 2.2 计数与判定边界（最容易被误用的部分）

| 事实 | 数量/语义 | 常见误用 |
|------|-----------|----------|
| `test/` 全部 `.ssa` | **64** | 把 64 当执行数 |
| `make check` 实际执行 | **50**（上游 glob `[!_]*.ssa`） | 把 14 个下划线前缀当"适配裁剪" |
| 引擎结果 | **49 PASS + 1 上游声明 SKIP**（`dark.ssa` 首行 `# skip arm64 arm64_apple rv64`） | 把上游平台 skip 当成适配跳过/或反之隐瞒 |
| 断言模式 | 13 项 stdout diff + 36 项返回码检查 | 只报"不崩溃"而不区分 |
| `qbe.ref` | 不随源码包发布；上游对汇编文本差异**只记录且恒 `return 0`** | 把 asm 文本一致当验收标准（或把 diff 当失败） |

### 2.3 为什么"编译通过 ≠ 运行证据"（E356 的镜像面）

编译器类包的"编译通过"只说明**编译器自己**编译成功；生成代码是否正确，只有执行才知道。
E356（chibicc，固定 x86-64 目标）证明在 armv8 上这类运行证据**不可能**，其方法是"双平面"替代证明；
qbe 自带 arm64 后端证明它**可以**——能出运行证据时，证据链就必须完整且可核数：
`SSA → arm64 汇编 → 设备内 cc 链接 → 原生执行 → stdout/返回码比对`。

## 3. 方案（可复制）

1. **驱动最小补丁**：`tmp=${TMPDIR:-/tmp}/qbe.zzzz`（1 行；默认行为不变、无平台宏、无绝对路径）。
2. **配方环境契约**：
   - `make -j1 SHELL=sh CC=<conf> CFLAGS="-std=c99 -O2 -g -Wall -Wextra -Wpedantic"`（R9/R33）；
   - `build()` 内、`can_run(self)` 时执行 `TMPDIR=<build>/qbe-test-tmp CC=<conf> sh tools/test.sh all`（R51 层 1）；
   - 原生路径不设置 `TARGET`（避免交叉/qemu 分支）；
   - 无 `install(1)`（设备实测）→ `package()` 用 `copy()` 安装 `bin/qbe` + LICENSE + docs；
   - OHOS 下若 `/data/service/hnp/bin/binary-sign-tool` 存在则自签名（设备无该工具，跳过）。
3. **消费者 E2E（test_package，12 断言）**：
   `-h` usage、`-t?`=arm64、两份最小 SSA（hello stdout 相等 / 计算值退出码 42）、非法 SSA 非零拒绝；
   真实执行打包后的 `bin/qbe`（删除 bin 必失败，满足 R34/L1e 破坏性验证）。
4. **验收判定**：以行为为准；编译通过、汇编文本一致都不算数。

## 4. 验证命令与全量结果

```sh
# ① fail-first（未打补丁，设备实测）
sh tools/test.sh all
#   → 49 of 50 tests failed!（逐项 cannot open '/tmp/qbe.zzzz.s'）
# ② 修复后（设备 + conan create 内两次复验）
TMPDIR=<build>/qbe-test-tmp CC=<clang> sh tools/test.sh all
#   → 49 [ok] + 1 上游声明 skip + 0 fail；"All is fine!"
# ③ 消费者 E2E
QBE_BIN=<pkg>/bin/qbe QBE_TEST_CC=<clang> bash test_package/test_qbe.sh
#   → qbe consumer E2E passed: target=arm64 hello='hello from qbe' exit=42
```

门禁链：`conan-verify` G0–G4 PASS（G2 内全量复跑）→ 本地 CI 门禁 1/1（L0/L1/L1e/L4/L5 PASS，L2 非阻断）→
W4 独立审计 0 P0/P1 → `finish` 完成；`test_package/MANIFEST.yml` 逐项列出 50 个用例与运行模式。

## 5. 与现有知识库的关系与增量（查重）

| 条目 | 与本条的关系 | 本条增量（不得被当作其重复） |
|------|--------------|------------------------------|
| E002（`/tmp` 只读 → TMPDIR，P014） | **事实层相同**：`/tmp` 只读、TMPDIR 可写 | 本条是**驱动硬编码变体**：脚本写死路径、环境变量不可覆盖，只能最小补丁；且本条重心不在 `/tmp`，而在"设备内运行证据链 + 契约 + 判定边界" |
| E052（config.status tmpdir 变体） | 同族不同面（configure 生成物 vs 测试驱动） | 同上；且 E052 的方案是源码内固定目录，本条的方案是默认保持的 `${TMPDIR:-/tmp}` |
| E356（chibicc：固定目标无运行证据 → 双平面） | **互补**：该类问题"出不了运行证据"的一面 | 本条覆盖"**能**出运行证据"时的完整方法论：证据链构成、契约清单、计数口径、判定边界（asm diff 非失败） |
| E387（LLVM lit 框架配置与最小子集） | 邻接：同属 LLVM/编译器测试族 | E387 是**框架层**（lit.cfg/site 属性/包内工具签名/子集选择）；本条是**零框架、独立后端自带的最小 E2E 驱动**，且给出行为验收口径 |

**draft-review 预审结论**：`create`（疑似新知）——最高相似 E356 score=0.19（sig=0.25 / kw=0.02 / cat=0.25 / phase=0.33），
远低于灰区阈值 0.30 与 merge 阈值 0.55；详见 §9。

## 6. 复用面（本仓语料内的类成员）

| 包 | 类别 | 与本条的关系 |
|----|------|--------------|
| `chibicc` 1.0.24.1 | C 编译器（固定 x86-64 目标） | 反面参照（E356）：无法在 armv8 出运行证据 |
| `tcc` 0.9.27mob | C 编译器（含 arm64 后端） | 同类成员：旧笔记已出现"make test 会失败（测试程序需要签名）"——"测试必须真的执行产物"的另一形态 |
| `scc`、`cc65`、`sdcc` | 编译器/交叉编译器 | 同类成员：测试套件生成并执行产物（交叉类只编译不执行） |
| `nasm`、`yasm`、`binutils` | 汇编器/工具链 | 同类成员：assemble → link → run 的 E2E 形态 |
| `llvm`/`clang`/`gcc` | 工具链 | 超集；测试框架层的问题见 E387 |

一般化：**任何"生成代码并执行"的软件**（代码生成器、JIT、DSL 编译器、模板引擎的编译测试）在设备内做
端到端验收时，都适用本条的契约与判定边界。

## 7. 适用范围与边界

- **适用**：上游测试套件在构建期执行生成代码、且驱动可做最小补丁（或可在配方侧等价注入）的包。
- **不适用/不覆盖**：
  - 交叉编译 + qemu 路径（本平台原生执行不需要，属另一环境契约）；
  - 仅编译不执行的交叉工具链（无法给出运行证据，按 E356 类处理）；
  - ELF 签名/执行门禁问题（E077 家族，属另一类问题，本条目不混入）；
  - `/tmp` 只读本身的一般性事实（归 E002/E052，本条只引用）。
- **判据**：只要验收宣称"测试通过"，就必须能回答三个问题——
  ① 执行了什么（分母与模式）；② 跳过了什么、谁声明的；③ 结果如何比对（行为而非文本）。

## 8. 证据索引

- 归档：`archives/q/qbe/1.2/`（`reports/conan-create.log`、`reports/test-report.md`、`test_package/MANIFEST.yml`、`notes.md`）
- 失败/修复前后对照：`tmp/qbe-evidence/raw-test-unpatched.log`、`tmp/qbe-evidence/test-patched.log`（设备侧，仓库外留存）
- 上游驱动与事实：`tools/test.sh`（第 7 行；`binref`/`TARGET`/`extract` 逻辑）、`Makefile`（`config.h` 生成）、`test/`（64 个 `.ssa`）

## 9. 预审记录（draft-review）

命令：`python3 scripts/ohc-run.py draft-review DRAFT-9848-qbe-device-e2e-runtime-evidence --json`

- 质量预检：signature ✅ / root_cause ✅ / rec ✅
- 相似正式条目 TOP3（相似度 = 0.55×签名片段 + 0.30×关键词 Jaccard + 0.10×类别 + 0.05×阶段）：

  | 条目 | score | signature | keywords | category | phase |
  |------|-------|-----------|----------|----------|-------|
  | E356（chibicc：固定目标无运行证据→双平面） | 0.19 | 0.25 | 0.02 | 0.25 | 0.33 |
  | E327（monorepo 结构） | 0.04 | 0.00 | 0.00 | 0.17 | 0.50 |
  | E486（引导构建交错执行与 .codesign） | 0.01 | 0.00 | 0.00 | 0.00 | 0.25 |

- **三态建议：`create`（疑似新知）**；与最高相似条目 E356 的 0.19 远低于灰区阈值 0.30，更远低于 merge 阈值 0.55。
- 人工核对要点：E356 是本条的**互补面**（该类问题"出不了运行证据"的一端），差异已写入 §5；
  E002/E052 未进入 TOP3（关键词与签名重合度低），但其事实层覆盖已在 §5 显式承认并声明增量；
  另两条 TOP 命中（E327/E486）与编译器证据链无关，属检索噪声。
