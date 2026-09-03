# minilua 5.4.7 for HarmonyOS

minilua 将 Lua 5.4.7 合并为一个可嵌入 C/C++ 项目的单头文件 `minilua.h`。
本 Conan 配方按 header-only library 打包，不携带预编译库或命令行二进制。

## 软件信息

| 项目 | 值 |
| --- | --- |
| 名称 | minilua |
| 版本 | 5.4.7 |
| 上游仓库 | https://github.com/edubart/minilua |
| 构建系统 | Makefile（仅上游测试使用） |
| 许可证 | MIT |
| 依赖 | 无 |

## 使用方式

在一个 C/C++ 翻译单元中定义 `LUA_IMPL` 后包含 `minilua.h`，即可提供 Lua 实现；其他翻译单元只包含头文件。
定义 `LUA_MAKE_LUA` 可额外启用 Lua 命令行解释器实现。

## 验证

- 上游 `tests/Makefile` 的 `make -j1 test` 实际包含 2 个程序调用。
- `test_package` 通过 CMake 消费包并执行 6 项 API 断言。
- OHOS 设备端 Conan 构建与运行结果记录在对应版本目录的 `notes.md` 和 `reports/` 中。
