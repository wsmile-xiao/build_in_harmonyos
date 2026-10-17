# Chinese Calendar 1.0.3.r58 适配笔记

- 上游：Launchpad chinese-calendar revision 58 的 Qt5 版本；本配方使用官方项目的可复现源码镜像提交 `593d89df7956253618da38e91891fb76516daf46`。
- 构建系统：qmake + make。
- 依赖：qtbase-sql-dbus/6.11.1、qtsvg/6.11.1。
- 软件类型：桌面应用，软件级 `commands.json` 已声明。
- qmake 初次配置报 `Unknown module(s) in QT: sql svg`；根因是 Qt 模块分包的 `mkspecs/modules` 未自动合并。配方改用已发布的 `qtbase-sql-dbus/6.11.1` 并通过 `QMAKEPATH` 注入 qtbase-sql-dbus/qtsvg 前缀。
- Qt6 编译报 qtsingleapplication 使用已移除的 `QRegExp`；新增 `0001-qt6-qregular-expression.patch`，替换为 `QRegularExpression`。
- Qt6 编译随后报 `QTextCodec` 头文件不存在；该头仅被 Qt4 条件分支引用，新增 `0002-qt6-remove-qtextcodec-include.patch`。
- GitHub archive 端点出现超时；同一官方仓库和提交切换到 codeload URL，下载哈希保持 `dd5d6fa429a21017f6f42cd45a35cc8bbb5e87482daea11ad03abbfb18ff193b`。
- `ccbo.cpp` 的环境变量过滤仍使用 `QRegExp`；新增 `0007-qt6-replace-ccbo-qregexp.patch`，替换为 `QRegularExpression`。

- CI 首轮 L0c 检查发现 `test_package/` 缺少源码文件；新增 `chinese_consumer_test.cpp`，通过 CMake 编译并由 Conan `test()` 执行，修复后本地 `conan create` 通过。

## 测试边界

上游未提供单元测试或集成测试目标，因此没有上游测试可执行，也没有修改上游测试。适配测试属于新增鸿蒙消费者测试，不虚增为多个测试用例：同一次消费者测试验证三个交付物边界。

## 已知限制

应用是 GUI 程序，消费者测试不启动事件循环，避免在无显示服务器的 CI 环境中阻塞；测试只验证可执行入口和运行时资源完整性。
---

**编译结束**: 2026-09-09 16:45
**最终状态**: built
