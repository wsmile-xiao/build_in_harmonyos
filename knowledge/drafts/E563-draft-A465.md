# E563 — Conan 拒绝单字符版本；任务卡单数字版本的目录/配方分离归一化

## 错误特征

`conan create` 在 **导出配方阶段**（未触达任何源码/依赖）立即失败：

```text
======== Exporting recipe to the cache ========
ERROR: Invalid package version '3'
```

与构建系统、源码、网络完全无关——`version` 属性为单字符时必现。

## 触发条件

- 构建系统: 任意（conan 配方层问题）
- 阶段: conan create 导出（recipe export）
- 典型来源: 任务卡/上游版本为单个数字或单字符的包（如 rapidhash 任务卡版本
  `3`、disktype `9`、repo `2`）。

## 根因分析

`conan/api/model/refs.py` 的 ref 校验正则为
`^[a-z0-9_][a-z0-9_+.-]{1,100}$`：第一个字符组匹配 1 次，第二组要求
**1–100 次重复**，因此版本总长 ≥2。单字符版本 `3` 不匹配 → `Invalid package
version`。同时本仓库 CI 的 **L0n 分支门禁**按「分支名去前缀 == 包目录名-版本
目录」精确匹配（`rapidhash-3` ↔ `feat/rapidhash-3`），平台任务也按该分支名
关联——版本目录必须保留任务卡原值，无法直接改成 `3.0.0` 等合规形态。
两个约束夹住后，正确解法是把"目录版本"与"conan 制品版本"分离。

## 解决方案

### 推荐方案

1. 归档目录、分支、版本级 manifest 的 `version:` 字段**保持任务卡原值**
   （`3`）——过 L0n 精确匹配与平台关联；
2. 配方**不写字面 `self.version = "..."` 属性**，改用 `set_version()` 钩子把
   制品版本归一化为合规 slug（上游 tag 剥前缀：`rapidhash_v3` → `v3`；
   hfsm2 `Beta73` → `beta73` 同型）；
3. `test_package/MANIFEST.yml` 的 `package:` 字段与制品版本对齐
   （`rapidhash/v3`）；
4. notes.md 与版本级 manifest 用行内引用留证目录-制品版本对应关系。

注：L0m-3 的「目录版本 == conanfile version」检查只对字面 `version = "..."`
属性生效（`^\s*version\s*=\s*["']`），`set_version()` 形态天然不触发。

### 禁止做法

- ❌ 字面 `version = "3"`：conan create 必失败（见错误特征），且与源码无关，
  易误判为配方其他问题盲调。
- ❌ 把目录改成 `3.0`/`v3` 等合规形态迁就 conan：L0n 精确匹配失败
  （`rapidhash-3.0` ≠ 分支 `rapidhash-3`），且任务平台按分支名关联会断链
  （bs-thread-pool 实测 5 个 PR 返工链）。

## 验证

```bash
# 复现（rapidhash 3，配方字面 version="3"）:
conan create archives/r/rapidhash/3 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing --user=ohpcd --channel=stable
#   ERROR: Invalid package version '3'
# 修复后（set_version 归一化 v3）:
#   conan-verify G2 PASS，test_package 3 个消费者全部通过（2026-09-09 实测）
```

## 关联条目

- 相关: DRAFT-hfsm2-beta73-uppercase-tag-version-slug（大写 tag 的小写 slug
  归一化——三处同步小写化；本条是"长度不足 2"边界，解法为目录/制品分离）
- 相关: E416（包名目录 slug / 大小写不敏感 FS）
