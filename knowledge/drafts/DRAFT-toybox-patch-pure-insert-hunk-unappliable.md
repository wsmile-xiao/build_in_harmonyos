# DRAFT-toybox-patch-pure-insert-hunk-unappliable — toybox patch 对"纯插入 hunk"（无 `-` 行）在上下文行合计 ≥7 时误报 Hunk FAILED（内容逐字节一致、文件不改写）；把插入改写为相邻行 `-`/`+` 替换对形状即可稳定应用

> 状态: DRAFT（待查重/提升；Curator 返修版 R1–R7，2026-09-26）
> 证据: 设备 toybox 0.8.12 探针矩阵（落盘路径见"验证/证据"节）；目标文件 GNU config
> `timestamp='2018-05-05'`（globus_gsi_proxy_ssl 6.6 `build-aux/config.sub`，1834 行）。

## 真实问题（场景）

在 OHOS 设备端为 `build-aux/config.sub` 编写 ohos 白名单补丁时，"在 `android-linux)`
分支后插入 `linux-ohos)` 子分支"这一改动最自然的 unified diff 写法是**纯插入 hunk**
（hunk 内只有上下文行与 `+` 行、没有任何 `-` 行）。该补丁在设备 `patch` 命令
（toybox 0.8.12）上反复报 `Hunk 1 FAILED 137/137.`，而 hunk 上下文与目标文件
**逐字节一致**（tab/空格经 `od -c` 核对）。

## 实测矩阵（同一目标文件、同一插入内容，仅 hunk 形状不同）

| 探针 | 形状 | hunk 头 | 结果 |
| --- | --- | --- | --- |
| [0] | —（pristine 基线） | — | `/bin/sh build-aux/config.sub aarch64-unknown-linux-ohos` → `aarch64-unknown-linux-gnu-ohos`（rc=0，静默改写，见姊妹条） |
| [A] | 纯插入，前导上下文 4 + 尾随 3 | `@@ -137,7 +137,11 @@` | `Hunk 1 FAILED 137/137.`，rc=1，**文件未被修改** |
| [B] | 纯插入，前导 3 + 尾随 4 | `@@ -138,7 +138,11 @@` | `Hunk 1 FAILED 138/138.`，rc=1 |
| [C] | 纯插入，前导 3 + 尾随 3 | `@@ -138,6 +138,10 @@` | rc=0，正常应用 |
| [D] | **替换对**：插入点前一行上下文改写为内容不变的 `-`/`+` 对，后接 4 个 `+` 行 | `@@ -137,7 +137,11 @@` | dry-run rc=0、应用 rc=0，四处改动行 sed 抽查全部正确 |

经验规律（同一插入 4 行的前提下）：**上下文行合计 7（前导 4+尾随 3 或前导 3+
尾随 4）必然 FAILED；合计 6 可过**。仅约束"前导 ≤3"不充分（[B] 即反例）；
跨插入行数的普适边界未测，不建议依赖。

## 根因（归因标注：疑似，未做源码级定论）

toybox patch 的错误报告格式 `Hunk N FAILED <旧行>/<新行>.` 与 GNU patch 不同，
且失败时对目标文件**零改动**（容易误读成"已应用成功"）。结合 [A][B][C] 矩阵，
疑似 toybox patch 对 hunk 前缀做至多 3 行的 fuzz 式消解，纯插入 hunk 的上下文
合计超出其处理能力时直接判 FAILED；确切内部机制待 toybox 源码级核实。需要强调
的两条边界：

- **不是偏移问题**：本条所有失败案例的 hunk 上下文与目标文件零偏移、逐字节一致，
  与 E510 的"上下文偏移/fuzz 容差缺失"（GNU patch 带 `fuzz 2 (offset -145)` 仍
  成功的场景）是不同的失败类。
- **不是 conan 路径问题**：同一形状的原始补丁经 conan `apply_conandata_patches`
  （patch_ng，行号精确匹配语义见姊妹条）在 `conan create` 中正常应用、CI 全绿。
  本条只影响设备端 `patch` 命令路径（手动 dry-run/应用预检、构建脚本内 `patch`
  调用、非 conan 补丁管线）。

## 方案（修复形状，不改语义）

把"插入"改写为**插入点前一行上下文的 `-`/`+` 替换对（两行内容完全相同，语义
no-op）后跟 `+` 新行**，即探针 [D] 形状：

```diff
@@ -137,7 +137,11 @@
 			android-linux)
 				basic_machine=$field1-unknown
 				os=-linux-android
-				;;
+				;;
+			linux-ohos)
+				basic_machine=$field1-unknown
+				os=-linux-ohos
+				;;
 			*)
```

诚实权衡：补丁多出一对冗余的 `-`/`+` 行，可读性略降、`git diff` 审查时需多看
一眼确认其为 no-op；但它同时通过 toybox patch 与 patch_ng 两条路径，且不需要
任何环境依赖。备选形状：把纯插入并入相邻替换 hunk（合并 hunk，实测 [V2] 亦
rc=0），代价是 hunk 粒度变粗。

## verification_cmd（自包含探针序列）

行号与锚点均按 GNU config `timestamp='2018-05-05'` 版（`build-aux/config.sub`，
1834 行；其他版本行号漂移，先重新定位）。

```sh
mkdir /tmp/probe && cd /tmp/probe
tar xzf globus-gsi-proxy-ssl_6.6.orig.tar.gz   # sha256=2b26087089993bf69d6827e9ce01c1afbc34d9ca8bf9d63cbcd55b5aae370f5b
cd globus_gsi_proxy_ssl-6.6
/bin/sh build-aux/config.sub aarch64-unknown-linux-ohos
# [0] pristine 基线：输出 aarch64-unknown-linux-gnu-ohos（rc=0，静默改写对照）
patch -p1 < probes/hunk2.patch                # [A] 纯插入 @@ -137,7：预期 Hunk 1 FAILED 137/137（rc=1）
patch -p1 < probes/diag_pureinsert7_trail4.patch   # [B] 纯插入 @@ -138,7：预期 FAILED 138/138（rc=1）
patch -p1 < probes/diag_pureinsert6.patch     # [C] 纯插入 @@ -138,6：预期 rc=0（边界）
patch -p1 --dry-run < probes/v1_replace_style.patch && \
patch -p1 < probes/v1_replace_style.patch     # [D] 替换对形状：预期两次 rc=0
sed -n '129p;141p;144p;1412p' build-aux/config.sub   # 四处改动行逐行核对
/bin/sh build-aux/config.sub aarch64-unknown-linux-ohos   # 断言：原样输出（4 段）
/bin/sh build-aux/config.sub aarch64-linux-ohos           # 断言：aarch64-unknown-linux-ohos（3 段）
```

## 验证/证据（落盘）

- `/storage/Users/currentUser/tmp/oh-device-porting-v2/gsps66/probe-pureinsert.log`
  （2026-09-26 复跑：[0] 基线 + [A] FAILED 137/137 + [B] FAILED 138/138 + [C] rc=0）
- `/storage/Users/currentUser/tmp/oh-device-porting-v2/gsps66/probe-replace-pair.log`
  （2026-09-26 复跑：[D] dry-run/应用 rc=0 + sed 抽查 + 4 段/3 段断言双 PASS）
- conan 路径对照：同形状原始补丁经 `apply_conandata_patches` 应用成功，CI
  `.ci_logs/conan_build_globus-gsi-proxy-ssl_6.6.log`（patch_ng 路径 rc=0）
- 探针 harness：`/storage/Users/currentUser/tmp/oh-device-porting-v2/gsps66/hunks/`
  （hunk2.patch / diag_pureinsert7_trail4.patch / diag_pureinsert6.patch /
  v1_replace_style.patch）与 `probe_harness.sh`

## 适用边界

- 适用：设备端 `patch` 命令（toybox 用户态）应用 unified diff 的一切场景——
  手动预检、构建脚本内的 patch 调用、非 conan 补丁管线；写"纯插入"类改动
  （新增 case 分支、新增列表项）时一律优先替换对/合并 hunk 形状。
- 不适用：conan `apply_conandata_patches`（patch_ng）路径的形状问题（其约束是
  hunk 头行号精确匹配，见姊妹条）；GNU patch 环境（无此陷阱）。

## 查重（R3 重写；逐项差异与新增价值，"无重复条目"结论不成立）

| 条目 | 关系与差异 | 本组条目新增价值 |
| --- | --- | --- |
| DRAFT-autotools-config-sub-silent-ohos-triplet（digup 0.6.57） | 同一事件的姊妹条：讲 config.sub **语义**层静默改写与 Conan 注入条件；本条（主条）讲 patch **工具**层形状陷阱。机理主覆盖在该条，本条不重复其结论 | 补全"补丁写出来之后能不能被设备端工具链应用"这最后一公里；两条合起来才是完整闭环 |
| E510 | 同为 toybox patch 缺陷：E510 是上下文**偏移**/fuzz 容差缺失（内容有偏移才失败）；本条内容零偏移、纯插入**形状**即失败，失败类不同，修复也不同（形状重写 vs 工具前置）。其 GNU patch 前置方案被本条引用为 fallback | 澄清 toybox 失败的两个独立触发类（偏移 vs 形状），避免误用"换 GNU patch"掩盖形状问题 |
| DRAFT-no-tail-newline-hunk-unappliable | 同工具（toybox 0.8.12）、同错误签名形态（`Hunk N FAILED`、内容一致仍失败、文件不改写、易误判成功）；触发面不同：彼为"目标文件末行无换行 + 尾标记 hunk"，本条为"纯插入 hunk 且上下文合计 ≥7"，与尾换行无关 | 补齐 toybox patch 形状敏感性的第二触发类；两条合并可视为"toybox hunk 可应用性"主题的完整矩阵 |
| DRAFT-conan-patch-hunk-exact-line-offset | patch_ng 路径的行号**精确匹配**语义（跨版本行号漂移即失败）；本条是 `patch` 命令路径的**形状**敏感。两路径互不覆盖且判据相反：GNU patch `--dry-run` 通过不代表 patch_ng 接受（该条），toybox `patch` FAILED 也不代表 patch_ng 失败（本条实测） | 同一补丁在两条应用路径上的判据矩阵补全，防止"单路径验证即出结论" |
| DRAFT-mpsolve-3.2.3-config-sub-ohos-kernel-hunk-and-no-build-host-bypass | 2022-01-03 版 config.sub 的两道**响亮**关口与一键脚本假成功；本条主条与其无机理重叠，但共享同一教训："工具/脚本自报成功不是判据，必须真跑断言" | 提供"自报成功 ≠ 应用成功"在 patch 工具层的又一实例 |
| E007 | config.guess 无法识别 HarmonyOS（第一道门槛）；本条不涉及 guess 路径（输入恒为显式三元组） | — |
| E072 | config.sub 三处修改方案（ohos-linux 映射 / OS 白名单 / kernel-os 白名单），面向带 kernel-os 门的版本且失败**响亮**；本条面向 2018-05-05 版（无 kernel-os 门），语义级分级见姊妹条（次条） | 版本谱系中"旧版无响亮门、失败全静默"的一端 |
| E122 | kernel-os 校验缺 `linux-ohos*-` 的响亮失败；2018-05-05 版无该校验门（`case $kernel-$os` 0 处命中），本条不适用该机理 | 同上，版本差异实证 |
| E268 | patch-autotools-ohos.pl 在 2024+ 版 config.sub 上静默漏补内核门并自报 ✅；本条为手工补丁场景，无脚本守卫问题 | 同 mpsolve 条：警示信号来自脚本侧，本条警示信号来自工具侧 |

## 关系

- principles: [P-PATCH-001, P-PATCH-004]
- similar_to: [E510, DRAFT-no-tail-newline-hunk-unappliable, DRAFT-conan-patch-hunk-exact-line-offset]
- causes: [] / caused_by: [] / conflicts_with: [] / prerequisite_of: []
