# raygui 4.0 适配笔记

## 编译环境
- 构建系统: header-only（无构建族，v12.21 模板变体 A）
- 编译日期: 2026-09-13
- 编译器: clang 15.0.4（消费者测试经 conan ohos-aarch64 profile 交叉编译）
- 状态: built（合并发布后由 release 流水线确认 published）

## 编译步骤

1. 无编译阶段：`raygui.h`（5521 行单头文件）从源码树 `src/` 复制到包 `include/`。
2. `package_type = "header-library"`，`package_id` 清空（无构建依赖 os/compiler）。
3. 消费者测试以 `RAYGUI_IMPLEMENTATION + RAYGUI_STANDALONE` 编译完整实现并断言 API 行为（见"验证结果"）。

## 上游测试清点与运行（R51 四维账本）

静态清点（N_static）：上游 tag 4.0 源码**无自动化测试**。`examples/` 13 个目录均为交互式演示程序（依赖 raylib 窗口环境），`controls_test_suite` 为手动 GUI 检查套件，无断言框架、无测试注册入口。N_static = 0（如实申报，清点证据：全仓库无 TEST/assert 注册宏、无 ctest/pytest 入口）。

消费者测试（N_consumer=1）：`test_package/test_consumer.c` 以 `RAYGUI_IMPLEMENTATION + RAYGUI_STANDALONE` 编译完整实现（约 4000 行实现代码真实编译进测试程序），5 组行为断言：GuiGetState 启停往返、GuiLock/GuiIsLocked 往返、GuiSetStyle/GuiGetStyle 回读、GuiIconText 非空返回。conan create 内编译、链接、运行全部通过（PASSED）。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | init-build 解压后 `.work` 缺 `src/` 目录（tarball 完整） | 解压工具在 HMDFS 上的目录选择性丢失 | 手动 `tar --strip-components=1` 重解压，核对与 GitHub tag tree 一致后继续 |
| 2 | 默认依赖 raylib.h，OHOS 无 raylib 包 | raygui.h 322 行 `#include "raylib.h"` | 消费者测试改用 `RAYGUI_STANDALONE` 模式，不引入 raylib 依赖 |
| 3 | conan create 报 "Package type is 'library', but no 'shared' option declared" | header-only 无 shared 语义但 package_type 为 library | 改 `package_type = "header-library"`（归档 338 例先例） |
| 4 | STANDALONE 模式编译/链接八轮报错（undeclared BLANK/KEY_*、隐式 int、static 冲突、undefined RL_FREE/GetGlyphIndex 等） | raygui.h 实现段调用的宿主符号仅部分在 STANDALONE 声明区声明 | 后端符号一次性补齐三段式（见知识草稿 DRAFT-7353：include 前颜色宏/键码/RL_FREE 宏/不完整类型 typedef/类型化原型；include 后按声明区精确签名定义 stub；断言层用纯逻辑 API） |
| 5 | G1 要求 build()/export_sources()/补丁调用 | header-only 无编译但验证器要求结构完整 | 加 export_sources()（export_conandata_patches）与 build()（apply_conandata_patches，空补丁 no-op） |

## 源码修改

无补丁（patches 为空，header-only 直接分发；上游文件零修改）。

## 依赖版本

无外部依赖（raylib 经 STANDALONE 模式规避，不进配方 requires）。

## 验证结果

```bash
# W3（finish 内部）：conan create 干净构建 + test_package 消费者测试 → 通过（test_consumer PASSED，5 组断言）
# conan-verify：G0-G4 + L2/L4/L5 全绿，Verdict: PASS（reports/conan-verify-report.md）
# 上游自动化测试：0/0（上游无自动化测试，如实申报）
```

## 路径 B 判断（成立，已申报）

满足证据门槛，走路径 B：
- **可复用知识主题**：依赖宿主 GUI 后端的 header-only 库在无宿主平台的消费者测试模式（RAYGUI_STANDALONE 后端符号一次性补齐三段式）——适用于 raygui 新版本及 nuklear 类可插拔后端库；
- **查重**：draft-review 三态评估 create（最高相似 E171 仅 0.42 且关键词零重叠；E527/E500 均不同域）；
- **触发实例**：task 7353 conan-verify G2 八轮迭代链（V4–V12）；
- **真实验证**：修复后 conan create 全绿 + test_consumer 5 组行为断言通过；
- **交付物**：知识草稿 `knowledge/drafts/DRAFT-7353-raygui-standalone-backend.{kv,md}`（与配方同一原子 PR）、知识库扩展 Issue #2987（与 PR 双向关联）、PR 正文单列"路径 B 知识贡献说明"节。

## 注意事项

- raygui 4.0 tarball 顶层即仓库根；配方 copy 取 `src/raygui.h`（init-build 解压曾选择性丢 `src/`，已手动重解压并核对 GitHub tag tree）。
- STANDALONE 模式不是完备后端接口：官方 standalone 示例（16 stub）为旧版，4.0 签名与函数名有变化（GetMouseWheelMove 返回 float、GetCharPressed、LoadFileText、新增 7 个样式加载函数），且实现段仍引用未声明的宿主符号（含 changelog 声称移除的 MeasureTextEx 残留调用）。
---

**编译结束**: 2026-09-13 02:26
**最终状态**: built
