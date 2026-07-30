# Ada

Ada 是一个符合 WHATWG 规范的高性能 URL 解析库，使用现代 C++ 编写。它支持完整的 URL 解析、序列化和组件访问，包括 URLPattern 规范。

## 功能概述

- **URL 解析**：符合 WHATWG URL 规范的完整解析器
- **URLPattern**：支持 URL Pattern 规范匹配
- **IDNA**：国际化域名 (Internationalized Domain Names) 处理
- **C API**：提供 C 语言接口 (`ada_c.h`)，便于跨语言集成
- **单头文件**：支持 amalgamation 模式，生成单头文件 + 单源文件
- **CLI 工具**：`adaparse` 命令行工具，支持 URL 解析、图表输出、组件提取、批量处理

## OHOS 适配

### 已知问题

1. **C++20 std::ranges 不可用**：OHOS libc++ (clang 15.0.4) 缺少 `std::ranges` 算法实现（`any_of`, `all_of`, `replace`, `find_if`, `find_if_not`, `stable_sort`）。通过 `ranges_compat.h` polyfill 头文件解决，委托到经典 `<algorithm>` 迭代器函数。

2. **C++ 标准库链接**：CMake 不识别 OHOS/HarmonyOS 平台，不会自动链接 libc++。需要显式设置 `-DCMAKE_CXX_FLAGS=-stdlib=libc++` 和 `-DCMAKE_EXE_LINKER_FLAGS="-lc++ -lpthread"`。

3. **并行编译限制**：`make -j2+` 在 OHOS HMDFS 上失败（`mkfifo: Operation not permitted`），需使用 `make -j1`。

4. **安全弹窗**：首次执行 `adaparse` 二进制会触发 OHOS 安全确认弹窗（R7），在非交互 shell 中使用 `script -q -c` 绕过。

### 构建选项

| 选项 | 说明 | OHOS 默认值 |
|------|------|-------------|
| `ADA_TESTING` | 启用单元测试（需 CPM 下载 GTest + simdjson） | ON (探索) / OFF (Conan) |
| `ADA_TOOLS` | 构建 `adaparse` CLI 工具（需 CPM 下载 fmt + cxxopts） | OFF |
| `ADA_BENCHMARKS` | 启用基准测试 | OFF |

## 依赖关系

- **编译依赖**：无（纯 C++ 库，无外部依赖）
- **测试依赖**（仅 `ADA_TESTING=ON` 时）：GTest 1.15.2, simdjson 3.10.1（CPM 自动下载）
- **CLI 工具依赖**（仅 `ADA_TOOLS=ON` 时）：fmt 11.0.2, cxxopts 3.2.0（CPM 自动下载）
- **运行时依赖**：无

## 参考资料

- 官网：https://github.com/ada-url/ada
- WHATWG URL 规范：https://url.spec.whatwg.org/
- Conan 引用：`ada/3.3.0@ohpcd/stable`
