# DRAFT-appstream-1.2.0-ohos-docs-daps-optional — 文档校验工具 daps 缺失 → find_program(required:false) + 子进程跳过（as-validate_docs 仍运行）

> **Contributor**: pc2-19 | **Status**: DRAFT | **Updated**: 2026-09-20
> **Severity**: medium (2) | **Category**: build / docs / tooling / portability
> **Audience**: meson 项目文档校验测试依赖 daps（DocBook 发布工具）而目标平台无此工具的配方

## 触发（trigger）

- appstream 1.2.0（archives/a/appstream/1.2.0，R03）：docs/meson.build:172
  as-validate_docs 测试在 OHOS 运行报 `FileNotFoundError: 'daps'`。

## 症状（symptom）

```
Validating documentation with DAPS...
FileNotFoundError: [Errno 2] No such file or directory: 'daps'
```

两层问题：meson 侧 `daps_exe = find_program('daps')` 使 docs=true 配置直接失败；
即便配置通过，doc-build-helper.py daps_validate 仍硬调 `daps validate` 子进程。

## 机制（root cause）

as-validate_docs 真实校验分两步：gen_doc_valsec_exe（valsec-gen，C 程序，校验文档
标签段）与 daps validate（DocBook schema 校验）。daps 是平台级外部工具，OHOS 无
发布包；valsec-gen 已覆盖 AppStream 特有校验，daps 仅为通用 DocBook 兜底。

## 修复（fix）

- 0007-docs-daps-optional.patch：`find_program('daps', required: false)`，
  仅 daps 存在才注册 make-docs 构建目标；as-validate_docs 测试始终保留。
- 0008-docs-validate-daps-skip.patch：doc-build-helper.py 内 `shutil.which(daps_exe)`
  为空时跳过 daps 子进程调用（valsec-gen 真实校验已通过），返回成功。

## 验证（verification）

- meson test as-validate_docs → 1/1 OK（rc=0）
- create60 全量 meson test 11/11 通过。

## 适用边界 / 反例

- 适用：文档校验测试依赖平台级 DocBook 工具、且项目自带真实校验器（valsec-gen）
  的场景；
- 反例：daps 为唯一校验器时不可跳过；确需完整 DocBook schema 校验时须安装 daps。

## 关系

- 查重：grep "daps|docbook|as-validate_docs" 无命中；与候选 2（itstool 可选化）
  同族（平台缺工具→required:false 回退），但工具面不同（docs 校验 vs metainfo i18n）。
- similar_to: DRAFT-appstream-1.2.0-ohos-meson-itstool-join-optional；caused_by: []；
  prerequisite_of: []；conflicts_with: []

## 证据

- 补丁：patches/0007-docs-daps-optional.patch、patches/0008-docs-validate-daps-skip.patch
- 台账：archives/a/appstream/1.2.0/reports/knowledge-candidate-ledger.md 候选 10
