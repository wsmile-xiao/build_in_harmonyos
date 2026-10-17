# minilua 5.4.7 适配笔记

## 编译环境
- 构建系统: makefile（上游 tests/Makefile）
- 编译日期: 2026-09-02
- 编译器: clang/clang++
- 状态: built（OHOS Conan、消费者测试和上游测试均已通过；尚未进入 release upload）

## 编译步骤

源码顶层包含生成好的 `minilua.h`，上游测试位于 `tests/`。使用正确的顶层源码目录执行：

```bash
make -j1 test
```

该目标构建 `lua` 和 `example`，随后分别执行 `./example` 与 `./lua -e "print 'hello world'"`。

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `init-build` 的探索源码根只有 `tests/` 内容 | 初始化脚本检测到嵌套测试目录后将其提升为源码根，未保留同级 `minilua.h` | Conan 配方使用完整官方 tar.gz；上游测试记录以原始顶层源码执行结果为准 |
| 2 | 消费者测试辅助函数 `check` 与头文件内部函数冲突 | 定义 `LUA_IMPL` 时实现代码与消费者代码进入同一翻译单元，头文件内部静态符号仍可能与消费者局部符号重名 | 将测试辅助函数改名为 `verify_condition`；消费者使用该类单头文件实现时应避免通用内部符号名 |
| 3 | OHOS Conan 生成的 CMake 目标名不是命名空间形式 | 设备端 Conan 2.29.1 的 CMakeDeps 日志显示 `Conan: Target declared 'minilua'`，`minilua::minilua` 不存在，配置阶段因此报 target not found | 按设备实际生成的导出目标改为链接 `minilua`，重新运行 test_package |

## 源码修改

本版本无需源码补丁。`minilua.h` 已由上游 `gen.sh` 生成并随 v5.4.7 归档发布。

## 依赖版本

无第三方 Conan 依赖；仅使用目标平台 C 标准库、数学库和动态加载接口。

## 验证结果

```text
主机：Apple clang 21.0.0 / GNU Make 3.81
OHOS：Conan 2.29.1 / Clang 15.0.4 / CMake 4.1.2 / GNU Make 4.4.1
OHOS conan create：通过；包产物为 include/minilua.h 和 licenses/LICENSE.txt
OHOS test_package：1/1 可执行消费者通过，6/6 断言通过
OHOS 上游 make CC=clang -j1 test：2/2 通过（example、lua -e）
源码 SHA256：28087a2d7ea0216d4fca66ff5ef15392477d70c9dfbaca68c06c3278ea716835
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| `include/minilua.h` | 862497 bytes | 单头文件 API 与实现 |
| `licenses/LICENSE.txt` | 上游许可证文件 | MIT 许可证 |

配方不包含预编译二进制或库文件。

## 注意事项

这是 header-only 库。使用者必须只在一个 C/C++ 翻译单元定义 `LUA_IMPL`；`LUA_MAKE_LUA` 可额外启用命令行解释器实现。
