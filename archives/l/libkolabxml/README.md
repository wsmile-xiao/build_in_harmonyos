# libkolabxml

## 简介

libkolabxml 是 Kolab 项目的 XML 格式库（KDE PIM 生态的核心组件）：实现
Kolab v3 XML 格式（基于 xCal/xCard 标准的 Kolab 扩展）的序列化与反序列
化，覆盖 event/todo/journal/note/contact/configuration/freebusy/file
八类 PIM 对象。KDE PIM 的 Akonadi Kolab 资源、messageviewer 等组件通过
本库与 Kolab 群件服务器交互。

上游最后版本 1.2.1（2014），项目已停止维护。

## OHOS 适配

- **构建系统**：CMake（2.8.5 时代，需 `CMAKE_POLICY_VERSION_MINIMUM=3.5`）
- **核心适配**：CodeSynthesis XSD 工具链（xsdcxx/xsdbin）无法在交叉编译
  CI 运行 → 绑定代码离线预生成（`--std c++11`）+ libxsd header-only
  runtime 随 patches/ 分发
- **C++17 现代化**：std::auto_ptr → std::unique_ptr（+显式 std::move）、
  boost::thread_specific_ptr → C++11 thread_local、boost::thread →
  std::thread
- **依赖链**：xerces-c/3.2.5 + boost/1.90.0 + libcurl/8.5.0；
  上游测试用 qt5/5.15.19 + ecm/6.20.0

## 版本索引

| 版本 | 状态 | 说明 |
|---|---|---|
| 1.2.1 | built | 首次 OHOS 适配，上游测试 84/84 全过 |

## 依赖

- xerces-c/3.2.5（XML 解析，静态链入）
- boost/1.90.0（headers：uuid/scoped_ptr/lexical_cast；thread 用法已改
  thread_local）
- libcurl/8.5.0（URL 解析资源加载，动态链接）
