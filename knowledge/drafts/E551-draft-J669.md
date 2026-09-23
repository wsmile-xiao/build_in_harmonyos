# E551（草稿）：Qt5→Qt6 源码级 API 迁移组合方案（QML 应用移植模式库）

> 状态：pending-editor-review（随 fingerterm 1.4.16 PR 提交，主编确认最终编号）

## 错误特征（出现任一即在本文档射程内）

```
error: 'QTextCodec' file not found
error: no member named 'ForceIntegerMetrics' in 'QFont'
error: 'QString::KeepEmptyParts' was not declared
QML: XmlRole is not a type
QML: Cannot assign to non-existent property "xml" / "query"
QML: module "QtQuick.XmlListModel" is not installed
error: no member named 'setOrientationUpdateMask' in 'QScreen'
fatal error: 'qplatformdefs.h' file not found
error: no matching member function for call to 'append'
error: object of type 'QStringDecoder' cannot be assigned
ld: undefined symbol: Terminal::ch_ESC
```

## 根因

Qt6 对 Qt5 的成体系 API 清理，分四类：

1. **整类移除**：QTextCodec（→QStringConverter 族）、qplatformdefs.h
2. **更名族**：QtQuick.XmlListModel→QtQml.XmlListModel、XmlRole→XmlListModelRole、
   query(XPath)→elementName/attributeName
3. **属性语义变化**：XmlListModel 内联 `xml:` 串移除（只留 `source:` URL）；
   `Screen.angleBetween` 仍在（勿误改）
4. **隐式转换移除**：QString::append(int)→QChar、QByteArray↔QString 互操作、
   QString::KeepEmptyParts→Qt::KeepEmptyParts（命名空间迁移，语义不变）

附带两个工程坑：
- QStringConverter 删除拷贝赋值（成员不能声明值类型后赋值，用 unique_ptr）
- 类内初始化的 `static const char` 被 `fmt.arg(const char&)` odr-use 时需类外定义

平台坑（OHOS 特有）：
- Sailfish 私有 QScreen::setOrientationUpdateMask 上游 Qt6 没有
- conan 沙箱链接的 ELF 在沙箱外 exec 报 EPERM（签名校验），需 binary-sign-tool
  重签后才能做真实运行验证

## 解法（fingerterm 1.4.16 实证）

见配套 .kv 的 solution 字段（9 个迁移点全代码级）。

验证方法链：
1. conan create 全绿（W3）
2. binary-sign-tool 重签 → offscreen 实跑
3. QML 加载到 root object 无错 = 移植完整
4. forkpty 子进程行为验证 VT 引擎

## 降级方案

- 无 XmlListModel 需求：删菜单 XML 功能（可选特性）
- QTextCodec 名字集超 QStringConverter：requires qtcore5compat 兼容实现

## 查重结论

- E437/E438/E440/E441：Qt6 cmake 组件查找层（find_package），非源码 API 迁移
- E323/E343：Qt6 模块构建配置，非应用移植
- E077：ELF 签名重签（本文档引用不重复）
- 本条增量：**源码级 Qt5→Qt6 迁移模式库**（9 迁移点 + qmake→CMake + 验证方法链），知识图谱无覆盖

## 红线

- Screen.angleBetween 在 Qt6 仍存在（plugins.qmltypes 实证）——不要"顺手"删
- elementName 不是 XPath：只取子元素文本/属性，复杂查询需改 C++ 侧预处理
- conan create 通过 ≠ 可运行（EPERM 签名）；宣称"实测运行"必须有重签后证据
