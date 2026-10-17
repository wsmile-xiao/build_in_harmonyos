**DRAFT-psimd-0.0-simd-backend-activation-evidence — 单头 SIMD 封装库后端激活验证契约：OHOS clang 仅预定义 `__ARM_NEON`（无 `__ARM_NEON__`），编译通过与 API 断言均不足以证明后端激活，需"先于 include 的双拼写编译期门禁 + 不透明输入 + 指令级反汇编"三重证据**

对依特性宏预处理分发后端的单头 SIMD 库（psimd 型），打包成功与消费者 API 断言通过都不能证明 SIMD 后端真的激活。本任务真机实证了三层混淆：①OHOS SDK clang 只预定义 `__ARM_NEON`（两种语言模式一致），只查 `__ARM_NEON__` 的探针会误判；②-O3 把常量输入的向量路径完全折叠（实测折叠后二进制零向量指令）；③qfma 回退形态 `a+b*c` 在默认 -ffp-contract 下与 vfmaq 路径产生相同的融合数值与 fmla 指令。最小修复是三重证据契约，并用负例对照逐一验证（EVID-00..05，全部真机执行）。

**身份与当前结论**

| 字段 | 内容 |
|---|---|
| 草稿 ID | `DRAFT-psimd-0.0-simd-backend-activation-evidence` |
| 配套结构化文件 | `knowledge/drafts/DRAFT-psimd-0.0-simd-backend-activation-evidence.kv` |
| 当前状态 | 已有验证证据待审（真机 target-executed，见第 4 节） |
| 建议去向 | 新增模式（验证契约类） |
| 实际贡献者 | atomcode-executor（任务执行）；PR 作者以提交信息为准 |
| 来源任务/PR | psimd/0.0-git20200517.072586a 适配；PR 创建后回填 |
| 提取方式 | 新适配过程提炼 |
| 本次交付 PR | atomgit.com/OpenHarmonyPCDeveloper/build_in_harmonyos/pull/11245 |
| 包及配方版本 | psimd / 0.0-git20200517.072586a |
| 上游版本与源码 | 072586a71b55b7f8c584153d223e95687148a900（2020-05-17 快照，master HEAD）；https://github.com/Maratyszcza/psimd/archive/072586a71b55b7f8c584153d223e95687148a900.zip；sha256 dc615342bcbe51ca885323e51b68b90ed9bb9fa7df0f4419dbfa0297d5e837b7 |
| 知识来源提交 | 03cba630acc1ac72482017e8781a48c327289422（本 PR 功能提交；另有一个仅回填文档的后续提交） |
| 被验证提交 | 03cba630acc1ac72482017e8781a48c327289422（影子 CI 指纹一致；后续回填提交不改配方/test_package，关系见证据报告第 6 节） |
| 最后更新 | 2026-09-19 |

本草稿的验证结论是：在 OHOS clang 15.0.4（aarch64-unknown-linux-ohos，SDK 26.0.0.18_2）真机上，psimd 后端激活可由"双拼写宏门禁通过 + API 断言 12/12 + 反汇编 bsl=2/fmla=1（不透明输入）"完整证明；三个混淆因子（宏拼写、常量折叠、FMA 收缩）均有真机负例实证。仍未证明：armv7-no-neon 与 x86 目标上的静默退化路径（EVID-03 表明该路径在 aarch64 上因上游头自毁而不可构造）、OHOS 以外工具链的行为。

**1. 触发条件与可辨认现象**

| 条件 | 本次实际值 | 为什么影响结论 |
|---|---|---|
| 目标系统、架构、运行域 | HarmonyOS PC（HongMeng Kernel 1.12.0），aarch64，真机原生执行 | aarch64 NEON 为基线，宏必然有其一——正因如此拼写分歧更隐蔽 |
| 编译器及构建工具 | clang 15.0.4（0e01a01d567b…，aarch64-unknown-linux-ohos）；llvm-objdump 同 SDK；Conan 2.29.1 OHOS 适配版 | 宏集合与收缩行为均为该工具链实测 |
| 关键依赖及版本 | 无（psimd 自包含单头；测试仅 libc/libm） | 排除依赖变量 |
| 文件系统、路径、权限或硬件 | 真机 HMDFS；测试二进制原生执行未额外签名 | 无特殊条件 |
| 最小输入与前置步骤 | conan create（header-only 复制）→ test_package 消费者构建 -O3 | 复现路径即正常适配路径 |

首次可定位的失败（EVID-00，真机实测）：

```text
test_package/test.cc:25:2: error: "psimd backend gate: __ARM_NEON__ not defined on aarch64 - NEON paths (arm_neon.h/vbslq/vfmaq) would not activate"
```

建议错误签名（三个分支均在真实运行中出现过）：`neither __ARM_NEON__ nor __ARM_NEON defined|__ARM_NEON__ not defined on aarch64|use of undeclared identifier .float32x4_t.`

签名验证：失败样本命中——`-U__ARM_NEON -U__ARM_NEON__` 编译 test.cc 触发第一分支（EVID-04）；初版门禁触发第二分支（EVID-00）；无 NEON 宏 include psimd.h 触发第三分支（EVID-03，上游头自毁特征）。正常样本不命中——EVID-01 全绿日志中无任何分支。

**2. 根因与排除项**

因果链：**OHOS SDK clang 仅预定义 `__ARM_NEON`（不定义 `__ARM_NEON__`；标准 aarch64 clang/gcc 两者皆定义）→ 只检查 `__ARM_NEON__` 的消费者探针/第三方代码误判"无 NEON"；而单头 SIMD 库的打包是纯头文件复制、不打编译标志，宏求值完全发生在消费者编译时，打包方对后端选择零可见 → 消费者 API 断言的数值语义与后端无关，后端退化时多数仍通过 → -O3 又会把常量输入的向量路径完全折叠，指令级证据也随之消失 → 三层混淆叠加，『打包成功 + 测试通过』与『SIMD 激活』之间无验证链。**

| 可能原因 | 检查方法与证据 | 结论 |
|---|---|---|
| 打包丢失/篡改头文件导致后端退化 | 包内 psimd.h sha256 与源码包一致（e33f1b93…） | 已排除（纯复制） |
| OHOS clang 在 aarch64 上完全无 NEON 能力 | 宏转储：`__ARM_NEON=1`、`__ARM_FEATURE_FMA=1`（C/C++ 一致） | 已排除（拼写分歧而非能力缺失） |
| API 断言失败会暴露后端退化 | EVID-03：无 NEON 宏时 psimd.h 在 665 行硬编译失败，"静默假阳性"在 aarch64 上不可构造 | 已证伪原假设并升级结论（见边界） |
| qfma 融合数值可作后端证据 | EVID-05：回退形态 TU 完全收缩为 fmla（fmla=1，fmul/fadd=0） | 已证伪（forbid_1） |
| 常量输入的反汇编可作为证据 | 折叠对照：常量输入 -O3 构建向量指令总数 0 | 已证伪（须不透明输入） |

多输入同变：各负例仅改变单一变量（宏定义、表达式形态、输入透明性），其余条件与正例一致。

**3. 最小修复与选择条件**

1. 修改位置：`test_package/test.cc`——门禁置于 `#include <psimd.h>` **之前**（`#if defined(__aarch64__) && !defined(__ARM_NEON__) && !defined(__ARM_NEON)` → `#error`）；全部断言输入过 `opaque()`（`__asm__ volatile("" : "+r"(x))` 屏障）；`test_package/conanfile.py` 的 test() 在 ctest 外直接 `self.run()` 测试二进制留执行痕迹。
2. 为什么有效：双拼写门禁把 OHOS 拼写分歧下的误判与真实后端缺失都变成编译期硬失败，且先于被测头的自毁报错给出可行动信息；不透明输入使向量路径在 -O3 下不可折叠，bsl 族指令成为 vbslq 路径的可复核特征；两层合起来闭合验证链且不改上游行为契约（包内容、API 语义均不变）。
3. 复用前必须重新核对：目标架构（门禁条件针对 aarch64；armv7 需改写）；特征指令映射（blend→bsl/bit/bif、qfma→fmla，其他库按其 intrinsic 映射重选）；fmla 不可用作判据（EVID-05）；objdump 工具可用性。

实际修复来源：本 PR `test_package/test.cc`（功能提交 03cba630ac）。

```sh
# 真机采证命令（完整五步与日志见 reports/knowledge-evidence.md）
conan create archives/p/psimd/0.0-git20200517.072586a -pr:h <ohos-aarch64 profile> --build=missing
llvm-objdump -d <build>/test_psimd | grep -cE '(bsl|bit|bif)[[:space:]]+v'   # >0 = blend NEON 路径
clang++ -O3 -U__ARM_NEON -U__ARM_NEON__ -I<包 include> -c test_package/test.cc  # 预期 #error 触发
```

上面的命令适用于：OHOS aarch64 原生构建。回退方案：llvm-objdump 不可用时只能依赖门禁 + API 断言（证据降级，报告中标注）；未验证其他替代探测手段。

**4. 验证矩阵与证据绑定**

| 证据 ID | 类型 | 提交、环境与输入 | 命令/测试入口 | 实际结果 | 日志/附件、定位与哈希 |
|---|---|---|---|---|---|
| EVID-00 | target-executed | 初版单拼写门禁 test.cc，真机首次 conan create | conan create（同 EVID-01） | 编译期 #error 触发（原文见上） | conan-create.log 初版（已被重跑覆盖）；根因由宏转储独立证明 |
| EVID-01 | target-executed | 最终 test.cc（门禁+12 断言+不透明输入） | conan create … --build=missing | 退出码 0；ctest 1/1；12/12 断言；二进制原生执行 | job conan-create.log |
| EVID-02 | target-executed | EVID-01 产物 test_psimd（-O3） | llvm-objdump -d + grep 计数 | bsl 族=2（bsl/bif @0x1e80/0x1fb4）、fmla=1（@0x20fc）、其余向量指令 10 | job evid/evid-run.log |
| EVID-03 | target-executed | 无 NEON 宏（#undef/-U）include psimd.h | clang++ -U__ARM_NEON -U__ARM_NEON__ 编译 neg3 | psimd.h:665 `use of undeclared identifier 'float32x4_t'`——头自毁，假阳性不可构造 | job evid/evid-run.log |
| EVID-04 | target-executed | 最终 test.cc + `-U__ARM_NEON -U__ARM_NEON__` | clang++ -O3 -U… -c test.cc | 门禁 test.cc:33 触发（先于 include），签名第一分支命中 | job evid/evid-run.log |
| EVID-05 | target-executed | qfma 回退形态独立 TU（vector_size(16) 上 `a+b*c`，不透明输入，-O3） | clang++ -O3 neg5.cc + objdump | fmla=1（`fmla v0.4s, v4.4s, v2.4s`）、fmul/fadd=0——完全收缩 | job evid/evid2-run.log |

`EVID-*` 为本文内部编号，非知识图谱 E 编号。全部为真机实跑；原始日志保存在真机 job 目录 `$HOME/ohos-users/device-b/psimd-kb-20260919/`（conan-create.log、evid/evid-run.log、evid/evid2-run.log），关键摘录与哈希见同名证据报告。

**被验证文件范围**

| 文件或输入 | 验证时版本/哈希 | 与当前提交的关系 |
|---|---|---|
| conanfile.py / conandata.yml | PR 分支提交后回填（git blob） | 相同 |
| test_package/（test.cc、conanfile.py、CMakeLists.txt、MANIFEST.yml） | PR 分支提交后回填（git blob） | 相同 |
| 上游 psimd.zip | dc615342bcbe51ca885323e51b68b90ed9bb9fa7df0f4419dbfa0297d5e837b7 | 与 conandata.yml 一致；包内 psimd.h sha e33f1b93… 与源码一致 |
| 真机工具链 | clang 15.0.4（0e01a01d…）、Conan 2.29.1、SDK 26.0.0.18_2 | 外部环境（evid2-run.log 指纹） |

被验证提交之后的变化：无（PR 单提交交付，最终 HEAD 由 PR 记录）。

**测试统计**

| 测试层与明确范围 | 计数单位 | 库存 | 通过 | 失败 | 跳过 | 未执行 | 库存依据及未执行原因 |
|---|---|---:|---:|---:|---:|---:|---|
| 上游 psimd（整个源码包） | 用例 | 0 | 0 | 0 | 0 | 0 | 上游零测试：6 文件、无 test/、无 ctest 注册（notes.md 清点表 + 证据报告第 1 节） |
| test_package 消费者（test.cc） | 断言（CHECK 宏） | 12 | 12 | 0 | 0 | 0 | EVID-01 |
| 后端激活与反例实验 | 实验断言 | 5 | 5 | 0 | 0 | 0 | EVID-00..05（EVID-03 的预期由"假阳性演示"修正为"自毁边界"，为确定性结果） |

同一行满足 N = P + F + S + U。上游层通过率不适用（库存 0）。

结论的证据等级与限制：全部关键结论 target-executed；"可推广到其他 SIMD 封装库"部分为静态推断（宏分发结构相似），未在其他库逐一验证。

**5. 适用边界与禁止做法**

| 可复用前提 | 已验证范围 | 未验证或不适用范围 |
|---|---|---|
| 库依特性宏在预处理期分发后端，头文件安装即打包 | psimd 0.0-git20200517.072586a @ OHOS clang 15.0.4 aarch64 | 运行期 CPU 探测型分发（libjpeg jsimd，E100 领域） |
| 目标 aarch64、NEON 基线 | OHOS aarch64（宏拼写分歧实测） | armv7（NEON 可选，门禁条件需改写）；x86（SSE/FMA 路径）；OHOS 以外工具链的宏集合与 -ffp-contract 默认值 |
| 静默退化路径 | aarch64 上不存在（EVID-03：头自毁为硬编译错误） | 头仍可编译的目标（armv7-no-neon、x86 无 FMA）上"API 全过但无 SIMD"的假阳性风险仍在，未实测 |

| 错误做法 | 为什么不成立 | 可观察后果 |
|---|---|---|
| 用 qfma 融合数值或 fmla 指令证明后端激活（forbid_1） | EVID-05：回退形态在默认 -ffp-contract=on、-O3 下完全收缩为单条 fmla | 后端退化构建给出相同数值与指令，形成假阳性申报 |
| 门禁只查 `__ARM_NEON__` 单拼写 | EVID-00：OHOS clang 只定义 `__ARM_NEON` | 正常 OHOS 构建被误判失败，或探针逻辑反转后放过真实退化 |
| 门禁放在 `#include <psimd.h>` 之后 | EVID-03/04：被测头先在 665 行报误导性 `float32x4_t` 未声明 | 得到不可行动的报错，掩盖真实根因 |
| 常量输入 + 反汇编当证据 | 折叠对照：-O3 常量输入构建向量指令总数 0 | 误判"无 SIMD"或证据不可复现 |

能力缺失区分口径：宏双拼写均缺 → 门禁 #error（编译失败，可辨认）；objdump bsl 计数 0 → 证据不成立（申报失败）；断言失败 → 数值契约破坏（真实缺陷）；三者不可互相替代，也不可互相冒充。

**6. 与已有知识的关系及增量**

| 已核验的条目/草稿/前序PR | 已有内容 | 本次新增机制、边界或证据 | 建议处理 |
|---|---|---|---|
| E506 | libpng：编译器开 NEON 调用点而 CMake 源清单漏选 → 链接失败（build 期可见） | 本次补"不可见"侧：预处理分发无链接症状，纯打包视角零信号；给出消费者侧三重证据契约与三个混淆因子的负例实证 | 新增（互补） |
| E100 | libjpeg jsimd 运行期 CPU 能力探测符号缺失 | 机制不同（运行期探测 vs 预处理分发），仅引用为对照 | 引用 |
| E257 | header-only 配方需 no-op build() 过 G1 | 本次为又一实例（复用，不申报增量） | 复用 |
| E103/E321 | CMake 4.x 拒绝 <3.5 声明的修复 | 本次上游即该形态但 header-only 路径不触发 CMake（规避边界注记） | 复用+注记 |

检索范围与关键词：knowledge/graph/index.tsv 与 knowledge/drafts/ 检索 `psimd|NEON|__ARM_NEON|simd|backend|激活|objdump|反汇编|false-pass`（2026-09-19，基于远端 main f8f47d0d17）。最相近命中为 E506/E100（如上表）；未发现覆盖"预处理分发后端的激活验证契约"或"OHOS clang NEON 宏拼写分歧"的条目。E257/E103/E321 已存在。

是否属于同一任务重提或版本修订：否（psimd 首次入库）。复用知识：E257（no-op build）、E103/E321（规避路径）；不重复计作增量：上述既有内容本身。

**7. 来源索引与提交自检**

| 材料 | 路径或链接 | 固定版本及角色 |
|---|---|---|
| 上游源码 | github.com/Maratyszcza/psimd/archive/072586a71b55b7f8c584153d223e95687148a900.zip | dc615342…（被适配对象） |
| 修复实现 | test_package/test.cc（门禁+不透明输入+断言） | 功能提交 03cba630ac |
| 消费者/反例测试 | test_package/test.cc + evid/neg3、neg5（真机 job 目录，复刻形态源） | 功能提交 03cba630ac + 真机 job 目录 |
| 汇总证据报告 | archives/p/psimd/0.0-git20200517.072586a/reports/knowledge-evidence.md | 同 PR |
| 原始验证记录 | 真机 job $J/conan-create.log、$J/evid/evid-run.log、$J/evid/evid2-run.log | 2026-09-19 真机执行 |

提交前填写真实检查结果：

- [x] ID、两个文件名和 KV 的 doc_file 一致（DRAFT-psimd-0.0-simd-backend-activation-evidence）。
- [x] KV 字段均为单行，根因、签名、方案与本文一致。
- [x] 引用路径存在于各自声明的提交；新材料（草稿+证据报告+配方）均已纳入提交范围。
- [x] 包版本、上游版本、验证提交及正文测试统计一致（0 上游/12 消费者/5 实验）。
- [x] 每个关键结论均有证据；未执行与边界已标记（armv7/x86 静默退化路径未实测）。
- [x] 已检索重复材料并说明增量（E506/E100 对照，互补非重复）。
- [x] 普通 PR 升级来源提取表：不适用（新适配）。
- [ ] PR 创建后回填真实编号并核对远端文件（当前为提交前阶段）。

最终处理建议：可作为候选提交。
原 PR 升级建议：不适用（新适配）。
剩余问题及下一项具体动作：无（PR #11245 已创建，等待 AI 检视与官方 CI）。
