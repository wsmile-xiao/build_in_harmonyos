# psimd 0.0-git20200517.072586a 知识证据报告

- 任务：psimd C++ 适配（知识库扩展，路径 B）
- 真机：10.195.180.238:2222（HarmonyOS PC，aarch64，隔离 job `device-b/psimd-kb-20260919`）
- 日期：2026-09-19
- 状态：全部实验已执行；【实测】标记数据均来自真机原始日志（job 目录 `$J` = `$HOME/ohos-users/device-b/psimd-kb-20260919`）

## 0. 环境指纹【实测：evid2-run.log】

```text
HarmonyOS localhost HongMeng Kernel 1.12.0 #1 SMP Wed Apr 29 10:16:03 UTC 2026 aarch64 Toybox
clang version 15.0.4 (llvm-project clang 0e01a01d567b9acfce8edfdadb66a7b69f088fb0)
  target: aarch64-unknown-linux-ohos（OHOS SDK 26.0.0.18_2, harmonybrew）
Conan version 2.29.1（OHOS 适配版）
llvm-objdump：OHOS SDK 26.0.0.18_2 native/llvm/bin
本地 profile：ohos-aarch64-local sha256 367f2b79cbc3c511ccc3cd84b2ab56a84ad716b274bd3417ab7d1312d3b067de
  （settings 与仓库 ci/conan/profiles/ohos-aarch64 相同；仅把该 profile 中硬编码的
   /data/service/hnp 工具链路径换成本机 harmonybrew SDK 路径——CI worker 与本机路径差异，
   与 psimd 适配本身无关）
```

## 1. 上游事实

- 上游：https://github.com/Maratyszcza/psimd（归档只读，2024-05-27）
- 快照：072586a71b55b7f8c584153d223e95687148a900（2020-05-17，master HEAD，"Fix psimd_qfma_f32 for FMA-enabled x86 processors"）
- 源码包 sha256：dc615342bcbe51ca885323e51b68b90ed9bb9fa7df0f4419dbfa0297d5e837b7
- 解包文件清单【实测】：`CMakeLists.txt, configure.py, confu.yaml, include/psimd.h, LICENSE, README.md` —— 6 个文件，无 test/ 目录、无 *test* 源文件、CMakeLists 无 enable_testing/add_test → **上游零测试（R51 清点）**
- 后端分发关键行（源码静态定位）：
  - L32-34：`#if defined(__ARM_NEON__) || defined(__ARM_NEON)` → `#include <arm_neon.h>`（两种拼写都接受）
  - L693-700：blend 族依 `__ARM_NEON__ || __ARM_NEON` 走 `vbslq_*`
  - L664-672：`psimd_qfma_f32` 依 `defined(__aarch64__) || ...` 走 `vfmaq_f32`；标量回退 `a + b * c`
- 关键平台事实【实测宏转储，C++ 与 C 模式一致】：

```text
#define __ARM_FEATURE_FMA 1
#define __ARM_NEON 1
#define __ARM_NEON_FP 0xE
#define __aarch64__ 1
（__ARM_NEON__ 带尾下划线拼写：未定义）
```

## 2. 候选知识表（P1）

| 候选 | 触发前提 | 根因 | 修复机制 | 复验方式 | 最相近材料与实际增量 | 去向 |
|---|---|---|---|---|---|---|
| 单头 SIMD 库后端激活验证契约（OHOS clang 仅定义 __ARM_NEON） | header-only SIMD 封装库依特性宏预处理分发后端 | OHOS clang 宏拼写分歧 + 打包不打编译标志 + API 断言与后端无关 + -O3 常量折叠抹掉指令证据 | 双拼写编译期门禁（先于 include）+ 不透明输入 + objdump 指令计数 | EVID-01..05 | E506/E100 只覆盖"可见失败"（链接/符号）；无"后端激活证明"契约 | 新增（DRAFT-psimd-0.0-simd-backend-activation-evidence） |
| psimd.h 上游潜在缺陷：无 NEON 宏的 aarch64 上自毁 | aarch64 && !(__ARM_NEON__ \|\| __ARM_NEON) | qfma 守卫（`__aarch64__`）与 arm_neon.h include 守卫（`__ARM_NEON__\|\|__ARM_NEON`）不匹配 | 无需修复（OHOS 上 __ARM_NEON 已定义）；消费者门禁须在 include 之前 | EVID-03/04 | 属同一草稿的边界事实 | 并入上述草稿 |
| E257 复用（header-only no-op build） | 同 fp16/wide-integer | — | — | conan-verify G1/G4 | E257 已有 | 复用 |
| E103/E321 边界注记（上游 cmake_minimum_required(2.8.12)） | header-only 路径不调用上游 CMake | — | — | — | E103/E321 已有修复方案；本次记录"规避"边界 | 复用+注记 |

## 3. EVID 矩阵（全部真机 target-executed）

### EVID-00｜__ARM_NEON__ 单拼写门禁误触发（负例，根因证明）

- 事件：首次 conan create（初版 test.cc 门禁 `#if defined(__aarch64__) && !defined(__ARM_NEON__)`）在真机编译期即失败：

```text
test_package/test.cc:25:2: error: "psimd backend gate: __ARM_NEON__ not defined on aarch64 - NEON paths (arm_neon.h/vbslq/vfmaq) would not activate"
```

- 结果：门禁按设计工作了——它暴露了本机 clang 只预定义 `__ARM_NEON`（无尾下划线）的事实（第 1 节宏转储为证）。初版日志已被后续重跑覆盖；错误原文如上，宏转储为根因独立证据。
- 处置：门禁改为双拼写（与 psimd.h 自身守卫一致）。此误触发即草稿 error_signature 第二个分支的真实来源。

### EVID-01｜conan create + test_package【实测：conan-create.log】

- 命令：`conan create archives/p/psimd/0.0-git20200517.072586a -pr:h $J/ohos-aarch64-local -pr:b $J/ohos-aarch64-local --build=missing`（隔离 CONAN_HOME=$J/conan-home）
- 结果：**退出码 0**。ctest `1/1 test_psimd Passed`；直接 self.run 输出 `test_psimd: OK (psimd API verified; aarch64 NEON gate passed at compile time)`。
- 消费者断言：**12/12 通过**（splat/add/sub/mul/max/min/abs/blend_s8/signblend_f32/load/store/qfma 融合消去）。
- 测试二进制原生执行成功（未额外签名）。

### EVID-02｜指令级证据【实测：evid-run.log】

- 对象：EVID-01 构建的 test_psimd（-O3，Release）
- 命令：`llvm-objdump -d test_psimd | grep -cE '(bsl|bit|bif)[[:space:]]+v'` 等
- 结果【实测】：

```text
pos_bsl_count=2   （bsl v0.16b, v1.16b, v2.16b @0x1fb4；bif v0.16b, v1.16b, v2.16b @0x1e80）
pos_fmla_count=1  （fmla v3.4s, v1.4s, v0.4s @0x20fc）
其余向量指令 10 条（fadd/fmul/ldr q/str q 等）
```

- 对照（常量折叠混淆因子，同日实测）：初版测试用常量输入，-O3 折叠后同规格反汇编 **bsl=0、fmla=0、向量指令总数 0**——证明指令级证据必须配不透明输入（`__asm__ volatile("" : "+r"(x))` 屏障）才有效。

### EVID-03｜负例 A：无 NEON 宏时 psimd.h 自毁【实测：evid-run.log】

- 构造：`#undef __ARM_NEON__`/`__ARM_NEON` 后 include psimd.h（或 `-U` 编译，两者等价）
- 预期（设计时）：blend 走通用路径编译通过 → 演示假阳性
- 实际结果【实测】：**无法构造**——psimd.h 在 665 行硬编译失败：

```text
psimd.h:665:34: error: use of undeclared identifier 'float32x4_t'
                return (psimd_f32) vfmaq_f32((float32x4_t) a, ...);
```

- 结论（升级为更准确的知识）：aarch64 上"后端退化"不是静默假阳性而是**硬编译错误**——psimd.h 的 qfma 守卫（L664 `defined(__aarch64__)`）与 arm_neon.h include 守卫（L32-34 `__ARM_NEON__ || __ARM_NEON`）不匹配：宏缺失时 include 被跳过但 qfma 分支仍选中 vfmaq_f32。上游潜在缺陷（本任务无需修，OHOS 上 `__ARM_NEON` 已定义）；"静默退化"仅在头文件仍能编译的目标上可能（armv7-no-neon / x86 无 FMA），本真机未验证，保持边界标注。

### EVID-04｜负例 B：编译期门禁触发【实测：evid-run.log】

- 命令：`clang++ -O3 -U__ARM_NEON -U__ARM_NEON__ -I<包 include> -c test_package/test.cc`
- 结果【实测】：门禁在 test.cc:33 触发，先于 psimd.h include：

```text
test.cc:33:2: error: "psimd backend gate: neither __ARM_NEON__ nor __ARM_NEON defined on aarch64 - NEON paths (arm_neon.h/vbslq/vfmaq) would not activate"
```

- 附带发现：门禁必须置于 `#include <psimd.h>` 之前——初版把门禁放在 include 之后，-U 负例下 psimd.h 先在 665 行报 `float32x4_t` 未声明（误导性报错），门禁没有机会触发。已在 test.cc 注释中记录。
- 签名验证：失败样本命中（本条）；正常样本不命中（EVID-01 日志无该片段）。

### EVID-05｜负例 C：回退形态同样收缩为 fmla（forbid_1 实证）【实测：evid2-run.log】

- 构造：psimd_qfma_f32 的 `#else` 分支精确源码形态——`a + b * c` 作用于 `float __attribute__((vector_size(16)))`（因 EVID-03 所示 psimd.h 无法在无 NEON 宏下编译，负例用独立 TU 复刻同表达式与同向量类型），不透明输入，-O3，默认 -ffp-contract=on
- 结果【实测】：

```text
neg5_build=OK
neg5_fmla_count=1   （fmla v0.4s, v4.4s, v2.4s @0x1950）
neg5_fmul_fadd_count=0   （完全收缩，无独立 fmul/fadd）
```

- 结论：**fmla 指令存在性与融合数值都不能区分 vfmaq intrinsic 路径与标量回退形态**——草稿 forbid_1 的可执行证明。可区分的证据是：宏门禁 + blend 路径的 bsl 族指令（vbslq 专属映射）。

## 4. 包完整性【实测】

- 真实包目录（conan 缓存 `p/b/psimdad7ea6c9838bb/p/`）：`include/psimd.h` + `licenses/LICENSE`，无多余文件
- 源码树 sha（缓存 s/ 目录）与源码包内 `include/psimd.h` sha256 一致：`e33f1b932b322820ab8c8e0c85ca8f508b1d578e9551c45f8caf2f3b7a79ab5e`（纯复制，打包不改头文件）
- conan create 依赖图：`psimd/0.0-git20200517.072586a#6bf258d4...:6b129b06...` 无第三方依赖

## 5. 测试统计（分母逐层）

| 测试层与明确范围 | 计数单位 | 库存 | 通过 | 失败 | 跳过 | 未执行 | 库存依据及未执行原因 |
|---|---|---:|---:|---:|---:|---:|---|
| 上游 psimd（整个源码包） | 用例 | 0 | 0 | 0 | 0 | 0 | 上游零测试（第 1 节清点） |
| test_package 消费者（test.cc） | 断言（CHECK 宏） | 12 | 12 | 0 | 0 | 0 | EVID-01，conan create test 阶段 |
| 后端激活与反例实验 | 实验断言 | 5 | 5 | 0 | 0 | 0 | EVID-00..05（EVID-03 的"假阳性演示"目标修正为"自毁边界"，亦为符合预期的确定性结果） |

上游层通过率：不适用（库存 0）。

## 6. 影子 CI 门禁（L0/L1/L2/L4/L5）【实测】

- 运行：`run-ohos-shadow-ci.sh archives/p/psimd/0.0-git20200517.072586a`（task_type=pr，
  git archive 干净快照 + 隔离 CONAN_HOME/TMPDIR + 全局锁）
- 指纹：run `03cba630acc1-20260919T154256Z-30904`，commit=**03cba630acc1ac72482017e8781a48c327289422**
  （=本 PR 功能提交；本报告的回填提交在其后，配方/test_package/conandata 与该验证提交逐字节相同，
  差异仅为本报告与文档回填——验证提交与最终 HEAD 关系的明确声明）
- 设备侧偏差声明（透明记录）：影子运行使用设备本地 profile
  （`ohos-aarch64-local`，settings 与仓库 `ci/conan/profiles/ohos-aarch64` 完全一致，
  仅把该 profile 硬编码的 CI worker 工具链绝对路径 `/data/service/hnp/*` 换成本机
  harmonybrew SDK 路径——本机不存在 /data/service/hnp；不替换时 CMake test_package
  必然找不到编译器，与 psimd 配方本身无关）。runner 为设备本地副本，
  唯一改动是 CONAN_PROFILE 允许环境继承（原副本硬编码 ohos-aarch64）。

```text
L0_RESULT=pass: all checks passed
L1_RESULT=pass: test_package executed（ctest 1/1；test_psimd: OK；12/12 断言）
L2_RESULT=skip: no bin/ dir（header-only 无命令行产物，有据跳过）
L4_RESULT=pass: no patches
L5_RESULT=warn: no artifacts found（CI L5 只探测 bin//lib/；本包产物为 include/psimd.h
               + licenses/LICENSE，产物存在性已由第 4 节包完整性验证（sha256 与源码一致）
               与消费者实际编译运行共同证明——warn 不误读为产物缺失，也不冒充 pass）
Build Summary: Total 1 / Success 1 / Failed 0
```

判定（按 openharmony-pc-native-shadow-ci 判定口径）：L0/L1 pass；L2 为有证据 skip（纯头文件包）；
L4 pass；L5 warn 已读取并判断如上。影子 CI 为独立预验证，不替代官方 PR CI。

