# DRAFT-appstream-1.2.0-ohos-meson-itstool-join-optional — meson i18n.itstool_join 在无 itstool 平台的可选化回退

> **Contributor**: pc2-19 | **Status**: DRAFT | **Updated**: 2026-09-20
> **Severity**: medium (2) | **Category**: build-system / meson / platform / portability
> **Audience**: 所有上游用 `i18n.itstool_join` 生成翻译版 metainfo 的 meson 项目适配者

## 触发（trigger）

- appstream 1.2.0 OHOS 适配：`data/meson.build` 无条件调用 `i18n.itstool_join`
  （把 release notes 与 metainfo 翻译合并），meson i18n 模块硬性要求 itstool 程序。

## 症状（symptom）

```
../data/meson.build:27:21: ERROR: Program 'itstool' not found or not executable
```

`i18n.itstool_join` 内部 `find_program('itstool')`（required=True 语义），
配置期直接失败；itstool 无 OHOS 预编译包，pip/lxml 依赖也不可用。

## 机制（root cause）

- meson i18n 模块 `itstool_join` 无条件调用 `find_program('itstool')`；
- OHOS 平台无 itstool（XML 翻译合并工具，依赖 libxml2 Python 绑定，本机不可装）；
- 整段代码无 feature 选项控制，配置期即阻塞。

## 修复（rec）

补丁改为 `find_program('itstool', required: false)` 门控：

```meson
itstool = find_program('itstool', required: false)
if itstool.found()
    metainfo_i18n = i18n.itstool_join(
        input:  metainfo_with_relinfo,
        output: 'org.freedesktop.appstream.cli.metainfo.xml',
        mo_targets: i18n_result[0],
        its_files: [join_paths(meson.current_source_dir(), 'its', 'metainfo.its')],
        install: true,
        install_dir: metainfo_dir,
    )
else
    # OHOS 构建机无 itstool：跳过 metainfo 翻译，直接使用未翻译版本
    metainfo_i18n = metainfo_with_relinfo
endif
```

要点：不可得时 metainfo_i18n 回退为未翻译自定义目标产物，下游
`as-validate_metainfo.cli` 测试仍注册并运行（不把工具缺失写成测试跳过）。

## 验证（verification）

conan create 配置/编译通过；`meson test --list` 中 as-validate_metainfo.cli 仍在
（8 个配置可执行用例）；metainfo 生成路径正常。

## 适用边界 / 反例

- 仅限"翻译合并类"目标（release notes/metainfo i18n），非运行必需；
- 反例：若项目强依赖翻译版 metainfo（产品语义），需另配 itstool；
- 反例：无 itstool_join 使用（纯 gettext po/）项目不适用。

## 关系

- 查重：grep "itstool" 无既有条目；engine 命中 E296（meson Windows 交叉工具注入）无关。
- 草稿库无同面条目。

## 证据

- 补丁：`archives/a/appstream/1.2.0/patches/0002-itstool-optional.patch`
- 生成器目录 .pc 列表含 itstool 回退后的 metainfo 目标：`archives/a/appstream/1.2.0/reports/conan-create.log`
- 台账：`archives/a/appstream/1.2.0/reports/knowledge-candidate-ledger.md` 候选 2