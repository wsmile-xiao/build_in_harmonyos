# vnlog

vnlog 提供带列名的文本表格格式。本归档适配其原生 C 静态库、公开头文件与 `vnl-gen-header` 头文件生成器，供 HarmonyOS PC 上的 C/C++ 消费者使用。

## 适配边界

上游同一发布包还包含 Perl 命令行工具、Perl 模块和 Python 模块。本配方**没有**打包或宣称验证这些组件；目标机缺少 `List::MoreUtils`、`Text::Table`、`IPC::Run`、`Text::Diff` 与 NumPy。上游 `make check` 共有 8 个测试套件，本次只运行其中的 C API 套件（12 项检查）。

## HarmonyOS PC

- 无 Conan 包依赖；直接编译 3 个上游 C 源文件，避开上游 Makefile 所需但设备未提供的 `mrbuild`。
- `vnl-gen-header` 使用 Perl 核心模块，安装于包的 `bin/`；其余 Perl 工具不在此包中。
- 上游 C API 检查 12/12；Conan 安装后消费者测试 1/1，在 aarch64 HarmonyOS PC 真机通过。
- 消费者测试的临时输入写在 CTest 的可写工作目录，不调用可能落到只读 `/tmp` 的 `tmpfile()`。

## 上游

- [源码及文档](https://github.com/dkogan/vnlog)
- [v1.42 发布](https://github.com/dkogan/vnlog/releases/tag/v1.42)
