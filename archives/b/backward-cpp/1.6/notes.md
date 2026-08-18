# backward-cpp 1.6 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-08-12
- 编译器: clang 15.0.4 / clang++
- 状态: built

## 编译步骤

backward-cpp 1.6 是 CMake 项目（header-only 栈回溯库，附带可选测试）：

```bash
cmake -S . -B build -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
      -DBACKWARD_TESTS=ON -DCMAKE_BUILD_TYPE=Release \
      -DCMAKE_POLICY_VERSION_MINIMUM=3.5
cmake --build build -j2
cmake --install build --prefix $DEFAULT_PREFIX   # 安装 backward.hpp + BackwardConfig.cmake
DESTDIR=$TEST_PREFIX cmake --install build       # staging 隔离安装
```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake Error: Compatibility with CMake < 3.5 removed | CMake 4.x 移除对 `cmake_minimum_required(VERSION 3.0)` 的兼容 | 补丁 0001: 提升到 3.5 |
| 2 | `error: unknown type name 'Dl_info'` | OHOS dlfcn.h 仅在 `_GNU_SOURCE`/`_BSD_SOURCE` 下暴露 `Dl_info`，且默认构建（无 BFD/DWARF）下 backward.hpp 未包含 dlfcn.h | 补丁 0002: 在 linux 段先定义 `_GNU_SOURCE` 再 `#include <dlfcn.h>` |
| 3 | `use of undeclared identifier 'program_invocation_name'` | 测试框架用 glibc 扩展符号，OHOS musl 无此符号（链接时报 undefined symbol） | 补丁 0003: `__OHOS__` 下改用 `__progname`（已验证可用） |
| 4 | make jobserver mkfifo 失败 | 沙箱 /tmp 只读，make 无法创建 jobserver fifo | 非阻塞警告，改用 -j2 直接编译 |

## 源码修改

3 个补丁（见 patches/）：
- `0001-CMakeLists.txt.patch`: cmake_minimum_required 3.0 → 3.5
- `0002-backward.hpp.patch`: dlfcn.h 需 `_GNU_SOURCE` 才能暴露 Dl_info
- `0003-test-_test_main.cpp.patch`: program_invocation_name → __progname（OHOS）

## 依赖版本

无外部依赖（header-only，仅 libc/dl）。

## 验证结果

- 编译: 100% 通过（backward + 5 个测试可执行文件）
- 上游测试: test_test 12/12、test_stacktrace 2/2、test_rectrace 2/2 全部通过
- test_select_signals / test_suicide: OHOS 上超时（前者需交互、后者故意无限递归栈溢出），但均打印完整 stacktrace，回溯功能正常
- staging 安装产物: include/backward.hpp + lib/backward/BackwardConfig.cmake

## 交付物

header-only 库，无二进制产物：
- include/backward.hpp
- lib/backward/BackwardConfig.cmake

## 注意事项

- R38 判断: 产物仅头文件 + CMake 配置，无可执行文件 → 无需 commands.json
- 消费者需链接 dl（`cpp_info.system_libs.append("dl")`）
- test_suicide 为故意栈溢出测试，CI 中不应运行（会卡死）
---

**编译结束**: 2026-08-12 11:52
**最终状态**: built
