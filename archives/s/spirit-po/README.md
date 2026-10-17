# spirit-po

`spirit-po` 是基于 Boost.Spirit 的 header-only C++11 GNU gettext PO 文件解析与本地化库。

## 功能

- 解析 PO header、单复数消息和上下文消息。
- 提供 `gettext`、`ngettext`、`pgettext`、`npgettext` 风格 API。
- 不生成或依赖 MO 文件，运行时可直接读取翻译者交付的 PO 文件。

## OHOS 适配

- 版本 `1.1.2`，上游标签 `v1.1.2`。
- 无库构建系统；配方按 header-library 安装 `include/spirit_po/`。
- OHOS clang 严格 C++11 下，上游未限定 `uint` 会导致 `unknown type name 'uint'`；配方应用两个 portability 补丁改为 `std::size_t`。
- 上游单元测试 126/126 通过。libintl 对照测试的 206 个数据驱动用例因 OHOS 环境缺少 `libintl.h` 与 libintl 链接库而有据跳过；仅有 `msgfmt` 不能替代该对照运行时。

## 依赖

- `boost/1.90.0`（Boost.Spirit/Fusion/Optional/Variant 头文件）。

## 参考资料

- 上游仓库：https://github.com/cbeck88/spirit-po
- 上游标签：https://github.com/cbeck88/spirit-po/tree/v1.1.2
