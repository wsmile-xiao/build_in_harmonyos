# grantlee

Grantlee（steveire/grantlee）：Django 模板系统语义的 Qt/C++ 字符串模板引擎，KDE 生态广泛使用。

- 上游仓库：https://github.com/steveire/grantlee
- 许可证：LGPL-2.1-or-later
- OHOS 适配版本：见 `5.3.1/`（Qt5 线，依赖 qt5-qtbase/5.15.2）

## 产物

| 产物 | 说明 |
|---|---|
| libGrantlee5Templates.so | 核心模板引擎（lexer/parser/context/safestring/节点渲染） |
| libGrantlee5TextDocument.so | QTextDocument 富文本模板（占位符渲染进 HTML） |
| lib/grantlee/5.3/ 插件 | defaultfilters（字符串/数字/列表过滤器）、defaulttags（if/for/block/extends）、i18n（tr 标签）、loadertags（include/extends 运行时） |

## 使用

```cmake
find_package(Grantlee5 REQUIRED)
target_link_libraries(app Grantlee5::Templates)
```

```cpp
auto engine = new Grantlee::Engine(nullptr);
auto tpl = engine->newTemplate(QStringLiteral("Hello {{ name }}!"),
                               QStringLiteral("hello"));
Grantlee::Context ctx;
ctx.insert(QStringLiteral("name"), QStringLiteral("world"));
tpl->render(&ctx);  // "Hello world!"
```
