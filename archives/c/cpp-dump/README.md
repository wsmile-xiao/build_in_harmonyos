# cpp-dump

cpp-dump 是一个 C++17 header-only 调试输出库，可以用统一的 `cpp_dump()` / `cpp_dump::export_var()` 接口打印任意类型的值——包括 vector、map、set、tuple、可调用对象以及用户自定义类型，支持彩色输出、缩进与自定义格式化。

## 功能概述

- 单入口 `cpp_dump()` 宏与 `export_var()` 字符串化接口，覆盖标准容器、智能指针、用户自定义类型（需特化或成员函数）。
- ANSI 彩色输出（original / by_syntax 两种转义风格）、多行缩进、宽度/深度控制。
- 可定制日志标签（`log_label`：line / basename / fullpath / fixed_length 等）。
- CMake `INTERFACE` 目标；上游测试为 CTest 27 用例（含 readme 示例快照对比）。

## OHOS 适配

- 生产包为 header-only：`package()` 只安装 `cpp-dump.hpp` 与 `cpp-dump/`（35 个头）与 LICENSE，不产生 `.a`/`.so`，无 `commands.json`。
- 需要 C++17（profile `compiler.cppstd=17`）；设备 clang15 默认 std 低于 17 时 `-Werror` 报 `inline variables are a C++17 extension`。
- HarmonyOS 使用 libc++：`unordered` 容器迭代序与上游 `dump_variable_linux.txt`（libstdc++）夹具不一致，实测与上游 `apple`（libc++）夹具逐字一致；补丁在测试夹具选择分支最前加 `CMAKE_HOST_SYSTEM_NAME STREQUAL "HarmonyOS"` 选新增 `*_ohos.txt` 夹具，linux/apple/win32 分支原样保留。
- 上游 `log_label::fixed_length(0,40,0)` 夹具取 `__FILE__` 尾 34 字符，要求源码目录名恰为 `cpp-dump`（GitHub Actions 检出目录名）；配方 `build()` 把源码拷贝到 `<build_folder>/cpp-dump` 后 configure，上游测试零改动。
- 库源码零改动，5 个补丁全部落在 `test/` 夹具面。

## 依赖关系

- Conan 生产依赖：0（header-only，仅 C++ 标准库与编译器运行时 `<cxxabi.h>`）。
- 运行时依赖：无。

## 参考资料

- 上游仓库：https://github.com/philip82148/cpp-dump
- 上游主页（README）：https://github.com/philip82148/cpp-dump#readme
