# DRAFT-autotools-config-sub-ohos-table-hunk-tiering — 2018-05-05 版 config.sub 补 linux-ohos 的 hunk 必要性分级：4 段三元组只有 os 归一化大表 hunk 承载（缺它被 `-linux*)` 兜底 sed **静默**改写成 `<machine>-unknown-linux-gnu-ohos`，rc=0）；同族旧版补丁三 hunk 全不匹配、必须按目标版本字节重写

> 状态: DRAFT（待查重/提升；Curator 返修版 R1–R7，2026-09-26）。
> 定位: DRAFT-autotools-config-sub-silent-ohos-triplet（机理主覆盖，digup 0.6.57 /
> 2020-01-01 版脚本）的**跨版本细化**，非新机理；本条聚焦 2018-05-05 版行号锚点、
> hunk 必要性分级与跨版本补丁不可复用实证。姊妹条
> DRAFT-toybox-patch-pure-insert-hunk-unappliable 覆盖补丁交付的工具层形状陷阱。

## 真实问题（场景）

为 globus-gsi-proxy-ssl 6.6 自带的 GNU config 脚本
（`build-aux/config.sub`，`timestamp='2018-05-05'`，1834 行）写 ohos 白名单补丁，
目标：`--host=aarch64-unknown-linux-ohos`（conanfile 显式传入的 4 段形态）。
直接复用同族 2013 版 config.sub（globus-gsi-openssl-error 4.4 先例）的现成补丁：
dry-run 三个 hunk 全部上下文不匹配——行号/缩进全漂移（2013 版 maybe_os 块空格
缩进、2018 版 tab 缩进；大表行 2013 版在 1365、2018 版在 1408），必须按目标版本
字节重写。

## 根因（版本机理；行号按 2018-05-05 版）

1. **4 段输入** `aarch64-unknown-linux-ohos`（config.guess 产出 / 本包显式
   `--host` 形态）走 `case $1 in *-*-*-*)` 分支（**120 行**）：
   `basic_machine=$field1-$field2`、`os=-$field3-$field4` = `linux-ohos`——
   **不经过** maybe_os 列表（129 行）与 `linux-ohos)` 子分支（137 行），随后只由
   os 归一化大表（**1408 行** `| -linux-gnu* | -linux-android* \` 行）放行。
2. **大表缺 `-linux-ohos*` 时的静默改写**：`-linux-ohos` 不命中大表任何
   alternative，下落 **1446 行**兜底规则
   `os=\`echo $os | sed -e 's|linux|linux-gnu|'\``，os 变 `linux-gnu-ohos`——
   **完整三元组输出 `aarch64-unknown-linux-gnu-ohos`，rc=0、无告警**
   （pristine 设备实测；与 silent-ohos-triplet 条 digup 版实测一致化）。
   错误身份随后被 configure 全盘采信并落盘（`S["host_os"]="linux-gnu-ohos"` 形态）。
3. **3 段输入** `aarch64-linux-ohos`（Conan AutotoolsToolchain 默认注入形态）走
   `*-*-*)` ambiguous 分支（124-145 行）：需要 129 行 maybe_os 列表 hunk
   （+137 行 `linux-ohos)` 子分支显式化 vendor），再经大表 hunk 放行。
4. **版本谱系（hunk 必要性分级）**：
   - 本版本（2018-05-05）**没有** E122/E072/E268 所述的 kernel-os 校验门
     （全文 0 处 `case $kernel-$os`、无 `basic_os`）——即不存在响亮失败路径，
     缺大表 hunk 的失败 100% 静默；
   - 必需 hunk：**大表（1408 行）追加 `| -linux-ohos* \`**（alternative 以 `*`
     结尾，符合大表注释约定）；缺它 4 段形态必然静默错；
   - 可选对齐 hunk：129 行列表 + 137 行子分支（只服务 3 段输入，补齐后 3 段
     形态同样归一化正确，实测 ASSERT-3SEG PASS）。
5. 补齐后判据：4 段/3 段均原样输出 `aarch64-unknown-linux-ohos`
   （探针 [D] 双断言 PASS）；pristine 对照输出 `aarch64-unknown-linux-gnu-ohos`。

## 方案

三个 hunk（相对 `build-aux/config.sub`，conandata `strip: 1`；行号按 2018-05-05 版）：

1. `case $maybe_os in` 列表行（129 行）加 `linux-ohos*`——覆盖 3 段输入；
2. `android-linux)` 块收尾 `;;` 行（140 行）写成内容不变的 `-`/`+` 替换对后接 4 行
   `linux-ohos)` 子分支插入（`@@ -137,7 +137,11 @@`）——形状选择受设备端 toybox
   patch 约束，见姊妹条（纯插入形状在 toybox 上误报 FAILED）；
3. os 归一化大表 1408 行行尾追加 `| -linux-ohos* \`——**必需 hunk**，
   `@@ -1405,7 +1409,7 @@`（新起始行号计入前一 hunk 净增 4 行）。

补丁上下文按目标版本字节精确生成（maybe_os 块 tab 缩进、大表 tab+6 空格），
交付前做严格位置应用验证（本地逐字节模拟 + 设备 `patch` + conan
`apply_conandata_patches` 三重），并以 `config.sub` 输出断言收口。

## verification_cmd（自包含序列；行号按 2018-05-05 版）

```sh
mkdir /tmp/probe && cd /tmp/probe
tar xzf globus-gsi-proxy-ssl_6.6.orig.tar.gz   # sha256=2b26087089993bf69d6827e9ce01c1afbc34d9ca8bf9d63cbcd55b5aae370f5b
cd globus_gsi_proxy_ssl-6.6
/bin/sh build-aux/config.sub aarch64-unknown-linux-ohos
# pristine 基线：输出 aarch64-unknown-linux-gnu-ohos（rc=0）＝静默改写证据
patch -p1 --dry-run < patches/0001-config.sub-ohos.patch   # 预期 rc=0
patch -p1 < patches/0001-config.sub-ohos.patch             # 预期 rc=0
sed -n '129p;141p;144p;1412p' build-aux/config.sub          # 四处改动行逐行核对
/bin/sh build-aux/config.sub aarch64-unknown-linux-ohos     # 断言：原样输出（4 段）
/bin/sh build-aux/config.sub aarch64-linux-ohos             # 断言：aarch64-unknown-linux-ohos（3 段）
```

实测落盘（2026-09-26，toybox 0.8.12）：
`/storage/Users/currentUser/tmp/oh-device-porting-v2/gsps66/probe-pureinsert.log`
（[0] pristine 基线输出 `aarch64-unknown-linux-gnu-ohos` rc=0）、
`/storage/Users/currentUser/tmp/oh-device-porting-v2/gsps66/probe-replace-pair.log`
（[D] 应用后 4 段/3 段断言双 PASS + sed 四处抽查正确）；conan 路径 CI 日志
worktree `.ci_logs/conan_build_globus-gsi-proxy-ssl_6.6.log`（configure 以
`--host=aarch64-unknown-linux-ohos` 通过）。

## 适用边界

- 适用：自带 GNU config（2017-2020 代、无 kernel-os 门）的 autotools 包做
  linux-ohos 适配；同族不同版本之间复制 config.sub 补丁的场景；判断"哪几个
  hunk 是必需的"时按输入形态分级（4 段只靠大表 / 3 段需列表+大表）。
- 不适用：2021+ 带 kernel-os 校验门的版本（失败形态转为响亮，方案见 E072/
  E122/E268 与 mpsolve 条）；不使用 config.sub 的构建系统。

## 查重（R3 重写；逐项差异与新增价值）

| 条目 | 关系与差异 | 本条新增价值 |
| --- | --- | --- |
| DRAFT-autotools-config-sub-silent-ohos-triplet（digup 0.6.57，2020-01-01 版） | **机理主覆盖**（此前查重漏检，本条删除"无重复条目"结论）：静默改写产物 `linux-gnu-ohos`、hunk 分工隔离实验、`config.sub "$(config.guess)"` 判据、Conan 注入条件均以该条为准。本条与其**同机理、不同版本代际**：锚点从 134/1357/1397 行变为 129/1408/1446 行（且该版无 `basic_os` 结构）；补充其未覆盖的 2018 代"无 kernel-os 门→失败全静默"谱系 | 跨版本细化：给出 2018-05-05 版字节级锚点、必要性分级判据（4 段只靠大表）与同族补丁不可复用实证，可直接复用到同代包 |
| E510 | toybox patch 偏移/fuzz 缺失（工具层）；本条是 config.sub 语义层，正交。补丁交付的工具层陷阱由姊妹条（toybox 纯插入形状）承载，其 GNU patch 前置在本组两条中作 fallback | — |
| DRAFT-no-tail-newline-hunk-unappliable | toybox 对无尾换行末行 hunk 双路径不可应用；与本条无机理重叠（本条目标文件尾换行正常） | — |
| DRAFT-conan-patch-hunk-exact-line-offset | patch_ng 按行号精确匹配、跨版本行号漂移在 conan 路径**响亮**失败（ConanException）；本条的跨版本不可复用在该路径由其机理解释，另补 dry-run（GNU/toybox patch）路径同样全不匹配的实测 | 两条应用路径的失败形态互证：conan 路径响亮、patch 路径亦响亮（FAILED），而**漏 hunk** 的后果才是静默 |
| DRAFT-mpsolve-3.2.3-config-sub-ohos-kernel-hunk-and-no-build-host-bypass | 2022-01-03 版两道响亮关口（OS 列表 + kernel-os 表）+ 一键脚本假成功 + `--build/--host` 不可绕过；本条版本无第二道门，失败形态相反（全静默），且为手工补丁无脚本守卫问题——本条即该条机理的跨版本细化（次条定位）；另见 DRAFT-mpsolve-3.2.3-make-check-green-is-not-deliverable-green（"绿 ≠ 对"的同主题构建侧） | 版本谱系补全：2018（无门，静默）→ 2022（两道响亮门）→ 2024+（脚本守卫误判） |
| E007 | config.guess 无法识别 HarmonyOS；本条不涉及 guess 路径（输入为显式 `--host` 三元组） | — |
| E072 | config.sub 三处修改（ohos-linux 映射 / OS 白名单 / kernel-os 白名单），面向**有 basic_os/kernel-os 结构**的版本、失败响亮；2018-05-05 版无该结构，对应物是 maybe_os 列表 + os 归一化大表 | 给出旧代版本的结构映射关系（129 行列表 ↔ OS 白名单；1408 行大表 ↔ kernel-os 门的前身），防止按新结构检索漏判 |
| E122 | kernel-os 校验缺 `linux-ohos*-`（响亮）；2018-05-05 版全文无 `case $kernel-$os`（实测 0 命中），该门不存在 | 同上：明确"哪些版本没有这道门"与静默后果 |
| E268 | patch-autotools-ohos.pl 在 2024+ 版静默漏补内核门且自报成功；本条为手工补丁、无脚本守卫问题；但共同教训一致：**补丁来源方自报成功不是判据，必须真跑 config.sub 断言** | 把该教训延伸到手工补丁 + 旧版 config.sub 场景 |

## 关系

- principles: [P-AUTOTOOLS-001]
- similar_to: [DRAFT-autotools-config-sub-silent-ohos-triplet, DRAFT-mpsolve-3.2.3-config-sub-ohos-kernel-hunk-and-no-build-host-bypass, E007, E072, E122, E268, DRAFT-conan-patch-hunk-exact-line-offset, DRAFT-config-sub-ohos-hunk-shape-tiering]
- causes: [] / caused_by: [] / conflicts_with: [] / prerequisite_of: []
