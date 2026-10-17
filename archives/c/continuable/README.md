# continuable

`continuable` 是一个 C++14 异步、支持异常处理并可组合的 continuation/future
头文件库，提供 `then`、`fail`、连接操作和 future 转换等 API。

## 软件信息

- 名称：continuable
- 主页：https://github.com/Naios/continuable
- 许可证：MIT
- 语言：C++
- 构建系统：CMake
- 类型：header-only library

## HarmonyPC 适配

4.2.2 已按头文件库方式打包，提供 `continuable/` 头文件、CMake package
元数据及 `function2/4.2.3` 依赖。Conan 消费测试会编译并运行真实程序，验证
链式 continuation、`when_all` 和异常恢复。

上游 GitHub 源码归档不包含 Git submodule 内容，因此上游 12 个 CTest 用例在
设备上使用带递归 submodule 的独立源码检出验证；Conan recipe 本身只复制公开
头文件，不把测试依赖或示例依赖误装进运行时包。

## 版本

| 版本 | 状态 | 日期 | 说明 |
|---|---|---|---|
| 4.2.2 | built | 2026-09-02 | HarmonyOS aarch64 设备验证，依赖 `function2/4.2.3` |
