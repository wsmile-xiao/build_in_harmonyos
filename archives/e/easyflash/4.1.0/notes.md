# easyflash 4.1.0 适配笔记

## 编译环境
- 构建系统: {cmake|autotools|makefile|meson|custom}
- 编译日期: {2026-09-19}
- 编译器: clang/clang++
- 状态: {published|built|failed}

## 编译步骤

{用文字描述实际编译步骤，包括关键的 configure/cmake 命令}

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
{按需添加行}

## 源码修改

{如有补丁，列出文件名和修改内容；无则删除此节}

## 依赖版本

{列出本次编译依赖的具体软件版本}

## 验证结果

```bash
{验证命令和结果}
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
{有打包产物时添加；无则删除此节}

## 注意事项

{需要特别注意的点；无则删除此节}
---

**编译结束**: 2026-09-19 04:00
**最终状态**: published

## 知识候选台账（本轮全部非噪声候选）

| # | 候选 | 真实错误 | 根因 | 修复 | 验证 | 适用范围 | 四范围查重 |
|---|------|---------|------|------|------|---------|-----------|
| K1 | 无构建系统 C 库直编配方 | conan-init 默认 autotools 模板不可用；conan create package() "No files in this package!" | 上游无 configure/make/cmake/meson；Conan2 中 self.copy 不存在、tools.build:archiver 非合法 conf、package() 阶段 self.source_folder 不可用 | build() 内逐 TU 直编（CC/AR 环境变量）+ staging 头文件到 build_folder；package() 仅从 build_folder copy | conan create exit 0；双测试 ALL PASS | 任何无构建系统嵌入式 C 库 | graph/doc/drafts 无 exact/causal 重复；E307/E311 部分 trigger/solution 重叠 |
| K2 | 空占位必需配置宏 | 消费者 include ef_cfg.h 编译失败（EF_ERASE_MIN_SIZE 等无值） | 上游把平台相关配置留作占位符由使用者定义 | patches/0001 补 RAM 模拟布局值（4096/8/0x0/8192） | 补丁后全 TU 编译通过、conan create 复验 | 带空占位必需宏的头文件 | 无既有条目（E059 是 autotools aclocal placeholder，不同类） |
| K3 | 无 MCU flash 的平台移植 | ef_port.c 仅桩实现，ENV API 无法运行 | 移植层由使用者提供，OHOS PC 无 MCU flash | RAM 模拟 NOR flash（erase→0xFF、write 仅 1→0、首次 init 置位后保留内容） | 消费者 10/10、鸿蒙专项 13/13 | flash/KV/键值存储库的宿主测试 | 无既有条目；E287（fuzz 网络交互）不同类 |

## 七轴查重摘要（详见 knowledge/drafts/DRAFT-easyflash-4.1.0-no-build-direct-compile.md）

exact_duplicate=false, causal_duplicate=false, trigger_overlap=partial(E307/E311),
solution_overlap=partial(E311), combination_novelty=true, boundary_novelty=true,
test_migration_novelty=true；similar_to=E311, E307；无 caused_by/prerequisite_of/conflicts_with。

## 路径判定

path B（知识库扩展）= new_draft：候选已验证、可跨库复用、查重未命中/部分覆盖且存在新增差异。
草稿对：knowledge/drafts/DRAFT-easyflash-4.1.0-no-build-direct-compile.kv / .md（与归档同 PR 提交）。
