# KF6 ki18n_install(po) 生成强制 ALL 目录标硬依赖 PATH 上 msgfmt+python3，OHOS 无 gettext 工具链时构建 FATAL，须设 KF_SKIP_PO_PROCESSING=ON 或保障工具链

- 形态：knowledge/drafts 条目草稿（最终编号 Exxx 由知识库主编确认）
- 配套 kv：`knowledge/drafts/DRAFT-kf-skip-po-processing-gettext-toolchain.kv`
- 申报路径：B【知识库扩展】（L2 跨库工程模式层：配方树 54 个 conanfile.py 同模式实践 ≥3 处门槛；阻塞面为真实构建期 FATAL 探针三 case）
- 来源 run：libkomparediff2-26.04.0（权威 CI PASS；tarball po/ 实有 72 语言，真实承重）

## 1. 一句规则

`ki18n_install(po)` 在未设 `KF_SKIP_PO_PROCESSING` 时会创建 `pofiles-<md5>`/
`tsfiles-<md5>` 两个 `ALL` 构建目标，硬依赖 PATH 上可用的 `msgfmt`
（`find_package(Gettext)`）与 python3；OHOS 最小开发环境无 gettext 工具链时
构建在 `build-pofiles.cmake:24` 以 `FATAL_ERROR "failed generating"` 失败。
不做本地化交付的移植基线应显式设 `KF_SKIP_PO_PROCESSING=ON`，需要 i18n
能力时则必须先保障工具链。

## 2. 机理链（每环有独立可复现证据）

1. **守卫面**：`KF6I18nMacros.cmake:78 option(KF_SKIP_PO_PROCESSING ... OFF)`；
   `:113-116` 在 `KI18N_INSTALL` 开头 `if (KF_SKIP_PO_PROCESSING) return()`——
   开关是零成本的官方出口。
2. **延迟暴露**：未设开关时 `:140/:148` 创建 `pofiles-<md5>`/`tsfiles-<md5>`
   `add_custom_target(... ALL)`。configure 期**不报错**，失败被推迟到
   `make all` 必经的构建期（configure 通过 ≠ po 处理可行）。
3. **失败点**：构建期 `cmake -P build-pofiles.cmake` 逐语言调用
   `GETTEXT_MSGFMT_EXECUTABLE`（宏头 `:7 find_package(Gettext QUIET)` 从 PATH
   获取；OHOS 最小开发环境无 gettext——ki18n 配方宏头自带注释 "msgmerge not
   available in OHOS dev env"）。不可用时 `build-pofiles.cmake:24`
   `message(FATAL_ERROR "failed generating ${PO_DIR}")`。`tsfiles` 目标另需
   python3（`:9-11 find_program`，本设备 ki18n 配方内置回退
   `/data/service/hnp/bin/python3.12`）。
4. **承重量化**：libkomparediff2 26.04.0 tarball 的 `po/` 实有 **72 语言**
   `.po`——工具齐备时（探针 case1，hnp gettext 0.26）全部生成 .mo 成功，但
   工具链依赖与构建时间随语言数线性放大；工具缺失时（探针 case2）72 语言
   全量失败于同一 FATAL。
5. **归类**：构建系统对可选 i18n 工具链的硬依赖语义（kb 八分类"构建系统
   语义"），非库内 quirk。

## 3. 推荐修复（配方一行）

```python
# conanfile.py generate() / CMakeToolchain
tc.variables["KF_SKIP_PO_PROCESSING"] = "ON"
```

诚实权衡：牺牲 .mo 翻译目录（运行时 i18n API 回退源文/英文），只适用于以
"库能力可用"为目标的移植基线。配方树实测 **54 个 conanfile.py** 同模式
（`grep -rl KF_SKIP_PO_PROCESSING archives --include=conanfile.py`，
accessibility、alkimia、akonadi、bluez-qt、grantleetheme 等），L2 第二实例
远超 ≥3 门槛。

## 4. fallback（诚实权衡）

- **保障工具链、不开开关**：需要 i18n 能力时，PATH 上提供可用 msgfmt
  （本设备 hnp gettext 0.26 探针 case1 实测生成全部 72 mo）与 python3
  （宏有内置回退，仍建议显式暴露）。成本：gettext 工具链依赖 + 随语言数
  线性增长的构建时间/体积；换完整 i18n 交付能力。

## 5. 反模式

1. **删除 `po/` 目录或 patch 掉上游 `ki18n_install(po)` 调用**：污染上游
   构建声明、永久丢失 i18n 能力、上游升级必然冲突；官方开关本就是正解。
2. **只设开关却宣称"完整 i18n 适配"**：.mo 未生成、翻译运行时回退，
   能力声明与实际交付不符（态度审计"诚实划定已验证边界"）。

## 6. 去重与关系

- **确认去重证据**（2026-09-14 设备实测）：`grep -ril KF_SKIP_PO_PROCESSING
  knowledge/` 在 knowledge/graph（540 条 E*.kv）与 knowledge/drafts（1273
  文件）均 **0 命中**。任务指定的 E092/E090/E383 逐项评估：E092（CMake
  平台模块缺失诊断 WARNING）、E090（Meson host_system 白名单）、E383
  （Platform 模块缺失 → SONAME 缺失）均为**平台探测/链接语义**族，与本条
  的 **i18n 工具链依赖**机理不同——不适用，故 similar_to 不取。
- **E402**（toybox gzip 仅支持短选项，GNU 长选项致构建失败）：同族"平台
  工具能力缺失 → 构建失败 → 降级方案"，取为 similar_to。与
  `DRAFT-kf-metainfo-platform-whitelist-ignore-flag`（本 run 主条，平台探测
  门禁）互补不重复：一个在 configure 期卡声明门禁，一个在 build 期卡工具链。
- 检索词：KF_SKIP_PO_PROCESSING / ki18n_install / msgfmt / GETTEXT_MSGFMT。

## 7. 原则挂钩

`P-BUILD-001`（平台限制必须降级而非绕过——msgfmt 缺失属系统级工具面差异，
设 `KF_SKIP_PO_PROCESSING=ON` 是"识别限制类型后选择对应降级方案"的标准
落地，且翻译缺失被如实写入 PR 披露而非隐藏）。

## 8. 五项质量门槛自检

1. 规则式标题 + 问题类 slug（`kf-skip-po-processing-gettext-toolchain`，
   无库名-版本命名；库名仅进 source_event 当案例）——✔
2. rec + fallback（含诚实权衡）+ 2 条 forbid（reason+consequence）——✔
3. verification_cmd 自包含（printf + 真实宏 + 真实 po 目录 + 三 case 双向
   退出码，新 shell 可跑；不依赖本 run 日志路径，日志仅作归档引用）——✔
4. principles 挂钩（P-BUILD-001）、affected_scope 泛化句式、similar_to
   链 E402（E092/E090/E383 评估后不适用并明示）——✔
5. 本 run 配额 2/2：本条为次条（L2，54 处第二实例）；
   `DRAFT-kf-metainfo-platform-whitelist-ignore-flag` 为主条——✔
