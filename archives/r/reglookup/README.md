# reglookup

reglookup 提供 Windows 注册表 hive 的只读取证工具 `reglookup`、`reglookup-recover` 和公开的 `libregfi` C 接口。

## HarmonyOS PC 适配

上游 1.0.1+svn296 发布包以 SCons 构建，并把头文件、库搜索路径硬编码到 Unix 常见目录。目标机没有 SCons，公开制品仓也没有 SCons 工具包。配方按上游 `SConstruct` 的五个库源文件与两个命令程序列表，用 OHOS clang 直接构建，并把 talloc 的 Conan include/lib 路径显式接入；不安装上游 Python 扩展或 DocBook 手册。

上游没有注册测试目标或示例 hive。目标机上安装后的 `libregfi` 由消费者程序调用公开 `range_list` API，校验添加、查找、空隙和重叠处理，共 8 个断言。真实注册表 hive 的端到端解析尚未验证。

[Debian 上游源码归档](https://packages.debian.org/source/sid/reglookup)
