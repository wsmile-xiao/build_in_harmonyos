# 知识候选台账与查重报告 — ee 3.2.2

> 适配过程中真实发生、可验证、可跨库复用的知识候选。
> 查重范围：knowledge/graph/index.tsv、knowledge/graph/*.kv、knowledge/doc/、knowledge/drafts/。

## 一、知识候选清单

### 候选 K1：STM32 HAL 依赖嵌入式库在 OHOS 宿主上的模拟 HAL + 固定低地址 Flash 模拟

- **触发库**: ee 3.2.2（NimaLTD.I-CUBE-EE，STM32 EEPROM 模拟单文件库）
- **真实错误**: ① 编译失败——ee.h 依赖 `main.h`（STM32 HAL），OHOS 无此头文件；② 链接后段错误——ee.c 用 `uint32_t Address` 直接解引用 Flash 地址 `(*(__IO uint8_t*)(eeHandle.Address + i))`，64 位宿主上缓冲区地址若 >4GiB 被截断 → SIGSEGV（-no-pie 链接碰巧正常，默认 PIE 必崩）。
- **根因**: 嵌入式 MCU 库假定 32 位地址空间 + 直接地址解引用 + HAL 头文件耦合；OHOS 宿主没有 STM32 Flash 硬件与 HAL。
- **修复**: ① 提供模拟 STM32 HAL 的 `main.h`（FLASH_* 宏 + HAL_FLASH_* API 声明）；② 新增 `ee_sim_flash.c` 用 mmap 固定映射低地址 0x20000000 的 16KiB 缓冲区模拟 Flash：构造时置 0xFF（空态）、Erase=memset(0xFF)、Program=半字写入（1→0 与操作）、EE_Read 直接寻址命中缓冲区——具备真实可观察语义，非空壳 stub；③ conanfile 直接 clang 编译 + llvm-ar 归档（micro-ecc 范式）。
- **验证**: ① 默认 PIE 链接 smoke_test 全绿（capacity/readback/format/NULL 拒绝）；② 消费者用例（设备参数持久化服务）重启回读一致、格式化清空；③ conan-verify G2 干净构建 + W3 本地 CI 通过。
- **适用范围**: 依赖 STM32/Cortex-M HAL 且直接解引用 `uint32_t` 地址的嵌入式固件库移植到 64 位 OHOS/宿主的通用模式；模拟层需保证真实语义（0xFF 空态、擦除、编程、校验）而非空壳。
- **可跨库复用**: 是（同模式可复用于 ee 同类库、其他 STM32-PACK 组件）。

### 候选 K2：conan apply_conandata_patches 对"新增文件"补丁的格式要求

- **真实错误**: refresh-patch 生成的 `--- a/xxx` / `+++ b/xxx` 双前缀格式（git diff 风格）在 conan `apply_conandata_patches` 应用时报 "source/target file does not exist"。
- **根因**: conan 的补丁解析按 strip=1 处理时，`--- a/...` 源路径不存在的场景（新增文件）需要标准 `--- /dev/null` + `+++ b/...` 头部。
- **修复**: 用 `git diff --no-index /dev/null <file>` 生成标准新增文件补丁（`--- /dev/null` + `+++ b/<file>`），并清理绝对路径；同时清除 edit-tracker 的 added 记录避免 finish 的 refresh-patch 覆盖。
- **验证**: 补丁 dry-run 通过 + conan-verify G2 / W3 通过。
- **适用范围**: 所有通过 patches/ 新增文件的无构建系统库配方。
- **可跨库复用**: 是。

### 候选 K3：W3 本地 CI（full 模式）命中其他库既有基线状态文件

- **真实错误**: finish W3 的 JC1 junk_check 以 full 模式（`git ls-files`）扫描全仓时，命中 main 上已提交的其它库运行时状态文件（cloog/.build-closed、cloog/.staging-verified、kics/.staging-verified），JC 拦截导致 W3 失败。
- **根因**: full 模式下 junk_check 扫描整仓 tracked 文件；这些空状态文件在提交前已存在于 main，非本库产物。
- **修复**: 基线隔离复验——记录精确路径与隔离前 SHA-256 → `git rm --cached` 临时移出 index（磁盘文件保留）→ 重跑 finish/W3 → `git reset` 恢复 → 核对恢复后 SHA-256 与隔离前一致（pre==post，均为空串哈希 e3b0c442…），且不写入本库 PR diff。
- **验证**: 隔离后 W3 通过（JC_RESULT=pass），恢复后文件哈希一致、`git ls-files` 恢复、未进入 staged/diff。
- **适用范围**: 任何遇到"其他库基线文件命中 full 模式门禁"的任务。
- **可跨库复用**: 是（流程性知识）。

## 二、七轴查重（K1 为主候选）

| 查重轴 | 既有条目（E045/E134/E166/E523/E424/E425/E426/E428/boxfort-draft/snmalloc-draft） | 本轮新增 | 结论 |
|---|---|---|---|
| exact_duplicate | 无任何条目以"STM32 HAL 依赖库 + 模拟 Flash + 固定低地址 mmap"为主题 | 完整新模式 | 非完全重复 |
| causal_duplicate | boxfort/snmalloc 均为"OHOS mmap 地址窗口/预留限制"（根因=平台 VA 上限） | K1 根因=库内 uint32_t 地址截断+缺 HAL，与平台 VA 上限无关 | 根因不同 |
| trigger_overlap | boxfort 触发于分配器高地址 MAP_FIXED EINVAL；snmalloc 触发于大预留 ENOMEM；E045 触发于 W^X | K1 触发于直接解引用段错误 + 缺头文件 | 部分重叠（都涉及 mmap/地址），触发场景不同 |
| solution_overlap | boxfort：运行时探测回退到低窗口；snmalloc：禁用 random_pagemap；E134/E523：Go linker 换路径 | K1：固定低地址 mmap 模拟 Flash + 模拟 HAL | 部分重叠（都用低地址 mmap 思路），方案形态不同 |
| combination_novelty | 无"模拟 HAL + 模拟 Flash + 固定低地址"组合条目 | 完整组合 | 新增 |
| boundary_novelty | boxfort 边界=高地址窗口；K1 边界=32 位地址截断（PIE 相关） | 明确 4GiB 截断边界 | 新增边界 |
| test_migration_novelty | 无 | 消费者用例验证持久化语义 + 鸿蒙专项 smoke | 新增 |

**查重结论**: K1 为**部分重叠但存在新增差异**——与 boxfort-39bit-VA、snmalloc-mmap 共享"OHOS 上 mmap 地址选择"的触发面，但根因（库内 32 位地址截断 vs 平台 VA 上限）、方案（模拟 Flash+模拟 HAL vs 探测回退/禁 mitigation）、适用边界（嵌入式固件库直接解引用 vs 分配器预留）均不同；K2/K3 为流程性知识，查重无命中。

## 三、路径决定

- `reuse_existing`: 否（无完整重复条目）
- `new_draft`: **是**——K1 已验证、可跨库复用、查重为部分覆盖且存在新增差异 → **路径 B（知识库扩展）**，同 stem 草稿为 `knowledge/drafts/DRAFT-ee-3.2.2-ohos-sim-hal-fixed-low-addr-flash.kv` + `.md`。
- `path_a_no_knowledge`: 否

## 四、关系字段

- similar_to: E045（mmap 平台限制）、DRAFT-boxfort-ohos-39bit-user-va-map-fixed-limit（低地址窗口）、DRAFT-snmalloc-0.7.5-ohos-mmap-va-reservation-limit（mmap 预留）
- caused_by: 无
- prerequisite_of: 无
- conflicts_with: 无
