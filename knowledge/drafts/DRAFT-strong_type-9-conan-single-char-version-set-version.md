# DRAFT: 任务头固定单字符版本时用 set_version() 归一化为上游 tag（目录-制品版本分离）

> 草稿来源：strong_type 9 R01（2026-09-19），与
> `DRAFT-strong_type-9-conan-single-char-version-set-version.kv` 配套。
> 待 promote 为正式 E 条目（需人工/AI 审核）。

## 问题（真实首错）

任务头 version=9（单字符），`conan-verify` G2 的 `conan create` 在导出阶段报：

```
======== Exporting recipe to the cache ========
ERROR: Invalid package version '9'
```

Conan 2.29.1 的 `RecipeReference.validate_ref()`（`conan/api/model/refs.py:148-154`）
以正则 `^[a-z0-9_][a-z0-9_+.-]{1,100}\Z` 校验版本号，要求版本号**最短 2 字符**，
单字符版本（"9"）不匹配，导出阶段即被拒。该校验无 conan 配置可放宽。

## 约束冲突

任务头已固定：`version: 9`、分支 `feat/strong_type-9`、归档目录 `archives/s/strong_type/9`。
L0n 分支门禁要求分支名与包名-版本精确匹配。直接改版本目录为完整版本（如 9→9.0）会破坏
分支/白名单一致性，且任务头未授权改版本。

## 方案（set-version-upstream-tag）

**目录-制品版本分离**：归档目录、分支、交付白名单保持任务卡单字符版本不动；
conanfile.py **不写字面 `version = "9"`**，改用 `set_version()` 将制品版本归一化为
上游 release tag（strong_type 上游 tag 为 `v9`）：

```python
class StrongTypeConan(ConanFile):
    name = "strong_type"
    # 无字面 version = "9"（Conan 单字符版本必被拒）

    def set_version(self):
        # 上游 release tag "v9"（conandata.yml sources.url 指向 refs/tags/v9.tar.gz）
        self.version = "v9"
```

修复后 `conan create` 导出 `strong_type/v9@...`，版本满足 ≥2 字符校验，
conan-verify G0-G4 + L2/L4/L5 全门禁通过（PASS）。

## 验证

- 修复前：`conan create .` → `ERROR: Invalid package version '9'`（G2 FAIL）
- 修复后：`ohc-run.py conan-verify strong_type 9` → G0/G1/G2/G3/G4 + L2/L4/L5 全 PASS，
  包引用 `strong_type/v9@ohpcd/stable`
- test_package 消费者 ctest 1/1 通过，独立复跑退出码 0

## 适用边界

- **适用**：任务头单字符版本（"3"/"9"），分支/白名单已锁死，上游 tag 形如 `v<N>`
- **不适用**：版本号已含点号/≥2 字符（直接写字面 version）；任务头允许改版本号与分支
  （走 version-rename，见 DRAFT-btyacc-3.0-conan-single-char-version）；包名大写等其他
  slug 问题（E416）

## 仓库既有实践

`set_version()` 分离方案已在多个归档验证：cronic/3（→v3）、ndpi/5（→5.0）、
dbskkd-cdb/3、cutmp3/4、rapidhash/3、tweeny/3、strong_type/9（本轮）。

## 与既有知识的关系

- **DRAFT-btyacc-3.0-conan-single-char-version**：同根因（Conan 单字符版本拒绝），
  但 btyacc 走 version-rename（改目录为 3.0）；本条目走 set_version() 目录-制品分离，
  适用于任务头固定单字符版本、无权改目录/分支的场景——两者是互补而非重复。
- **E470**（cppitertools）：版本元数据/目录版本一致性相关，不覆盖 set_version 分离方案。

## 反例与限制

- 反例：上游无 v 前缀 tag 且为多字符版本时无需本方案；任务头允许改版本时优先 version-rename。
- 限制：校验正则随 Conan 版本变化，证据基于 Conan 2.29.1（OHOS 适配版与 CI 同源）；
  set_version 返回值必须与 conandata.yml sources.url 的 tag 一致（v9 ↔ refs/tags/v9.tar.gz）。
