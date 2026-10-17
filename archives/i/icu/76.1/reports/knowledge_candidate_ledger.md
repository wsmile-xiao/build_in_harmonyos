# icu 76.1 知识候选台账与四范围查重

> 适配事件：icu 76.1 HarmonyOS PC（aarch64）适配（feat/icu-76.1，PR #8988）
> 任务类型：知识库扩展（路径 B 候选评估）
> 台账日期：2026-09-16

## 候选汇总

| 候选 | 真实错误 | 根因 | 修复 | 验证 | 适用范围 | 查重结论 |
|------|---------|------|------|------|---------|---------|
| C1 | configure 报 "Cross compiling but no --with-cross-build"（icu 交叉编译强制要求） | ICU configure 检测 host≠build 进入交叉模式后，强制要求 --with-cross-build 指向真实交叉构建树；CI 无 x86_64 侧真实 icu 构建树 | 在 build_folder 内创建**最小 icucross.mk + icucross.inc stub**（含 U_IS_BIG_ENDIAN/U_HAVE_ATOMIC 等少量变量 + 从 source/config/mh-linux 拷贝的平台 make 片段），仅用于满足 configure 参数校验；testdata 构建另需把已构建的 gentest 拷入 stub 的 tools/gentest/ | 本任务实测：configure 通过、make 完整成功（libicudata.a 静态数据打包 31.9MB、libicui18n 10MB、libicuuc 4.9MB）、消费者与鸿蒙专项测试运行通过 | 所有要求 --with-cross-build 的 ICU 版本（76.x/77/78 同源机制）；可类推到其他自举式（bootstrap）交叉构建库 | **部分覆盖 → 路径 B 新增**：E176 fallback 提及 --with-cross-build 但仅指向"预构建工具树"，未描述最小 stub 构造；DRAFT-gnustep-gui-ohos-autoconf-cross-probe 仅覆盖强制交叉模式三元组，不含 icucross.mk/icucross.inc 最小 stub |
| C2 | config.status 生成时 HMDFS 上 umask 077 导致 Permission denied | HMDFS 不支持 umask 077 语义 | 三步法：configure --no-create → 修复 config.status umask 077→022 → 运行 config.status | 本任务实测通过 | 所有 autotools 库 | **完全重复 → 复用** E011/E129/E206/E223（已有 4 条同根因条目） |
| C3 | conanbuild.sh 导致 /bin/sh SIGSEGV（Error -11） | 详见 E064 | 不 source conanbuild.sh，直接设 CC/CXX/AR/RANLIB 环境变量 | 本任务实测通过 | autotools 库 | **因果重复 → 复用** E064（已含 trigger-security-dialog + cache-file 双方案；直接设编译器变量是其实现变体） |
| C4 | ucptrietest/TrieTestSet1 golden 序列化 core dump（Signal 6） | cintltst ucptrie 16-bit 值宽 golden 测试在交叉 stub 平台宏下崩溃（U_HAVE_STRTOD_L/U_HAVE_XLOCALE_H stub 值与 host 实测不一致可能导致序列化路径差异）；非当前库配方可修项 | 待上游/平台层面确认；当前记为真实测试失败项（1/137），不影响消费者与专项验证 | 实测复现：`./cintltst /tsutil/ucptrietest/TrieTestSet1` 稳定 Signal 6；其余 136 项 [OK] | cintltst 套件该子测试 | **不成立（非知识）**：属测试运行观察，未产生可跨库复用方案；按测试台账如实记录 |

## 七轴查重（对 C1 —— 唯一可跨库复用新增差异候选）

| 轴 | 结果 | 说明 |
|----|------|------|
| exact_duplicate | false | 无既有条目描述"最小 icucross.mk/icucross.inc stub"构造 |
| causal_duplicate | false | E176 根因是 stubdata 动态链接器限制（--disable-tests 无关），C1 根因是 configure 交叉模式强制 --with-cross-build；两者不同因 |
| trigger_overlap | 部分 | E176 fallback、DRAFT-gnustep-gui 都涉及"交叉编译/configure"触发面，但触发点是 configure 参数校验，非动态加载或 conftest 执行 |
| solution_overlap | 部分 | E176 fallback_approach=cross-build 提到 --with-cross-build 概念，但方案是"使用预构建工具树"；C1 是"构造最小 stub 满足校验 + 运行期拷入 gentest"，未覆盖 |
| combination_novelty | true | 最小 stub（icucross.mk+icucross.inc 少量变量）+ testdata 阶段动态补 gentest 的组合无既有条目 |
| boundary_novelty | true | 适用边界明确：ICU 系列及自举式交叉构建库；反例：无需 --with-cross-build 的普通 autotools 库不适用 |
| test_migration_novelty | true | 该技术使 cintltst/intltest 测试可在交叉构建下构建与运行（testdata 构建依赖 stub 内 gentest） |

## 关系字段（C1 草稿）

- similar_to: E176（ICU 构建平台适配，同库不同因）、DRAFT-gnustep-gui-ohos-autoconf-cross-probe（同交叉模式触发面）
- caused_by: 无
- prerequisite_of: 无
- conflicts_with: E205 的 "Never use --build/--host" 仅针对 config.guess 缺失检测分支的绕过；C1 在三元组已正确区分 host/build 后满足 configure 参数校验，不冲突

## 路径决定

- `reuse_existing`: C2（umask，E011 家族）、C3（conanbuild.sh SIGSEGV，E064）
- `new_draft`: C1 —— 已验证（本任务真实构建+测试通过）、可跨库复用（ICU 76.x/77/78 同机制）、查重为部分覆盖且存在组合/边界/测试迁移新增差异 → **路径 B（知识库扩展）**
- `path_a_no_knowledge`: 不适用（存在有效新增知识）
- 草稿文件：`knowledge/drafts/DRAFT-icu-76.1-ohos-minimal-icucross-stub.kv` + `.md`（同 stem 配对），与 icu 76.1 归档文件进入同一 PR

## 候选观察（不建草稿）

- message2/spec JSON 测试数据缺失（intltest TestMessageFormat2 3 处 ERROR）：属上游 conformance 数据需网络获取，非代码/配方问题，记入测试台账，不产生知识条目。
