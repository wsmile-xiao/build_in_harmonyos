# ada 3.3.0 适配笔记

## 编译环境
- 构建系统: CMake
- 编译日期: 2026-06-30
- 编译器: clang 15.0.4 (OHOS SDK)
- 状态: published

## 编译步骤

```bash
cd $BUILD_SRC_DIR
mkdir -p build && cd build
cmake .. \
  -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
  -DCMAKE_BUILD_TYPE=Release \
  -DADA_TESTING=ON \
  -DCMAKE_EXE_LINKER_FLAGS="-lc++ -lpthread" \
  -DCMAKE_CXX_FLAGS="-stdlib=libc++"
make -j1
make install DESTDIR=$TEST_PREFIX
ctest --output-on-failure
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | `std::ranges::replace` 等算法不可用 | OHOS libc++ (clang 15.0.4) 缺少 C++20 ranges 算法实现 | 创建 `ranges_compat.h` polyfill 头文件，用经典迭代器算法委托实现 |
| 2 | 链接错误: undefined symbol `std::cout`, `operator new` 等 | CMake 不识别 OHOS 平台，未自动链接 libc++ | 添加 `-DCMAKE_EXE_LINKER_FLAGS="-lc++ -lpthread"` 和 `-DCMAKE_CXX_FLAGS="-stdlib=libc++"` |
| 3 | init-build 下载失败 | SSL 证书问题 + 网络超时 | 手动用 `curl -skL` 从 codeload.github.com 下载，使用 `--no-download` 重试 |
| 4 | make -j2 失败: mkfifo Operation not permitted | OHOS HMDFS 不支持 jobserver FIFO | 改用 `make -j1` |

## 源码修改

### 1. 新增 `include/ada/ranges_compat.h`
- Polyfill for C++20 `std::ranges` algorithms not available in OHOS libc++
- Provides: `std::ranges::any_of`, `all_of`, `replace`, `find_if`, `find_if_not`, `stable_sort`
- Delegates to classic `<algorithm>` iterator-based functions via `std::begin()`/`std::end()`

### 2. 修改 `include/ada/common_defs.h`
- 在 `#include <version>` 后添加 `#include "ada/ranges_compat.h"`
- 确保所有翻译单元在使用 `std::ranges` 前已包含 polyfill

### 补丁文件
- `patches/0001-include-ada-common_defs.h.patch` — common_defs.h include 修改
- `patches/0002-add-ranges-compat-header.patch` — 新增 ranges_compat.h 文件

## 依赖版本

- CPM 自动下载 (仅测试构建):
  - GTest 1.15.2
  - simdjson 3.10.1
- 无运行时 Conan 依赖

## 验证结果

### 单元测试 (ctest)
```bash
$ ctest --output-on-failure
100% tests passed, 0 tests failed out of 180
Total Test time (real) = 7.18 sec
```

测试涵盖:
- WPT URL 规范测试 (ada::url + ada::url_aggregator)
- WPT URLPattern 测试
- IDNA toASCII/toUnicode 测试
- C API 测试 (ada_parse, getters, setters, etc.)
- URLSearchParams 测试
- basic_fuzzer 模糊测试

### CLI 功能测试 (adaparse)
26 项功能测试，23 项通过。详见 `reports/functional-test-report.md`。

测试涵盖:
- `--help` / `-h` 用法输出
- URL JSON 解析
- `-d` 图表模式
- `-g` URL 组件提取 (host, protocol, pathname, origin, href, hostname, port, hash, search, password)
- `-b` benchmark 性能统计
- `-p` 文件批量处理
- 无效 URL 错误处理
- 管道批量处理

发现 2 个上游 bug:
1. `--get username` 不可用 (print_part 分支逻辑错误)
2. 管道模式退出码始终为 1 (ternary 表达式反转)

## 注意事项

- ada 是纯 C++ 库，默认构建为静态库 (libada.a)
- C++20 标准要求 (CMAKE_CXX_STANDARD=20)
- OHOS 平台需要 `-stdlib=libc++` 和 `-lc++` 链接标志
- 测试需要 CPM (CMake Package Manager) 下载 GTest 和 simdjson
- adaparse CLI 工具需要 `ADA_TOOLS=ON` 和 CPM 下载 fmt + cxxopts
---

**编译结束**: 2026-07-01 16:24
**最终状态**: published
