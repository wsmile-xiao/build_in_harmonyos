# DRAFT-conan-patch-hunk-exact-line-offset — Conan 2 补丁 hunk 行号精确匹配

## 问题类
Conan 2.x 的 `apply_conandata_patches`（patch_ng 库）应用 conandata.yml 注册的补丁时，
按 hunk 头 `@@ -N` 声明的旧文件行号做**精确匹配**；GNU patch 则按上下文在整文件范围
模糊搜索（offset/fuzz），行号偏差 ±2 仍可应用。两者语义不一致导致：
GNU patch `--dry-run` 通过的补丁，Conan 仍可能拒绝。

## 事件与证据（第二实例，与 connect-proxy #9036 互证）
libjpeg9 9f 适配 round-01：E007 的 config.guess 平台识别补丁自 libjpeg/10（2024 版
config.guess）移植到 jpeg-9f（2021 版），@@ -193 头沿用旧文件行号，而 jpeg-9f 的实际
锚点在 191（偏移 2 行）。GNU patch --dry-run 通过；conan create 失败：

- 证据锚点：`ci/round-01/full.log:179` —— `ConanException: Failed to apply patch: .../patches/0001-config.guess.patch`
- 前驱 WARN（同日志内）逐行给出：`hunk no.1 does not match source file at line 193` 与 expected/actual 对照行
- 失败发生在 build() 的 apply_conandata_patches，源码归档/配置/编译路径均正常
- 修正（@@ -193 → @@ -191）后 round-02/round-03 conan create 全绿，上游 make check
  与 test_package 全过——构成「行号重锚即修复」的因果闭环

## 自包含最小复现/自检探针（本条独有）
不跑 conan 即可判死活（对任意补丁与目标文件）：

1. `grep -m1 "^@@" 补丁` —— 取 hunk 起点旧行号 N 与首个 context 行；
2. `sed -n "Np" 目标文件` —— 输出必须与该 context 行逐字节一致（剥去 diff 前缀空格）；
3. 不一致 ⇒ Conan 必失败，GNU patch --dry-run 的通过不构成反证。

最终判据：干净 source_folder 实际调用 apply_conandata_patches（或直接 conan create）。

## 修复
以目标文件实际行号重写 @@ 头（`grep -n` 定位锚点 → 起始行号 = 锚点前 context 行数，
增删行数同步更新新/旧计数），随后实测应用。

### fallback
只有行号漂移的旧补丁时：先在原始源码副本用 GNU patch（允许 offset）应用成功，
再用 `diff -u 原始 已应用` 重新生成行号精确的补丁替换，重生成后仍按探针 + 实际应用双验证。

## 关联与查重定位

### DRAFT-conan-patch-cross-version-cumulative-hunks（connect-proxy 1.105，PR #9036）——姊妹条
- **同类证据**：error_signature 三串完全相同（hunk no.N does not match source file at
  line X / source file is different / ConanException: Failed to apply patch）；root_cause
  同机理（patch_ng 严格行号定位、无 GNU patch 模糊 offset）；forbid_1 近逐字相同
  （GNU patch dry-run 通过不等于 Conan 可应用）。
- **分工边界（明示）**：该条的**第二层**——同 stem 多补丁顺序应用时第 N 个补丁必须
  基于「前 N-1 个补丁应用后的累计态」行号——**本条不覆盖**。本条聚焦**单补丁跨版本
  移植的 re-anchor**（锚点内容相同、行号不同的单一 unified diff），是该问题类的第一层
  最小独立形态；两篇为姊妹条分工。
- **本条独有增值**：
  1. 自包含最小探针（grep @@ + sed Np 逐字节比对，无需跑 conan 即可判死活）；
  2. 单补丁跨版本 re-anchor 的聚焦修复法（@@ 头按目标文件重定位）；
  3. **第二实例证据**：libjpeg9 round-01:179 与 connect-proxy #9036 构成同类两实例互证，
     说明这是 patch_ng 通用语义而非孤例；
  4. 与 E526 strip 语义联动：patch_ng 应用语义有两层坑（剥离层级 + 行号匹配），
     pre-CI 校验须**同时镜像两者**（本条 × E526 的二维校验矩阵）。

### 机理佐证挂接
- **E475**（patch_ng strict exact hunk offsets，fuzz=False 语义）：从 Conan 引擎侧
  印证精确匹配是 patch_ng 的设计行为而非偶发；
- **E279**（跨补丁引擎的上下文锚定/zero-context hunk）：从补丁形态侧印证行号锚定
  在不同引擎间不可互换，零上下文块尤甚。

### 评估未挂接（Curator 可选项 E510）
E510（toybox patch 缺路径层级/fuzz 处理，需前置 GNU patch）属设备侧 patch 工具链
替代问题：同为「引擎间 fuzz 语义差异」家族的第三引擎数据点，但失败面在设备工具链
选型而非 conan patch_ng 应用路径，故不入 `similar_to`，留此存档。

### 建议主编评估
同类两实例（connect-proxy #9036 + libjpeg9 round-01）证据已足，建议晋升时评估：
合并为单条更强条目（第一层 + 第二层 + 双实例），或以本条（第一层/单补丁/探针）与
姊妹条（第二层/多补丁累计态）明确姊妹分工并互挂 similar_to。

## 原则钩子
- P001：config.guess/config.sub 平台脚本补丁须保持原生平台检测语义（本条补丁即 E007 家族）
- P003：对生成文件的修改必须沉淀为 .patch（补丁可应用性是硬前提）
- P011：补丁须可追溯、可复现（hunk 头行号对准目标文件是可复现的一部分）

## 备注
本条由原 DRAFT-E007B-config-sub-ohos-old-ts 拆出扶正（Curator 审计：config.sub 主体与
E007/E072/E122 查重覆盖，已降级经验仓；本条为独立可复用问题类）。证据中的 round 日志
为本 run 目录内相对路径。

## 状态
DRAFT — 结构五项与探针/证据锚/fallback/P 钩已经 Curator 复核通过；本轮按审计清单补齐
查重定位（姊妹条分工 + 机理挂接 + E510 评估 + 合并建议），Curator 预授权 CONFIRMED。
