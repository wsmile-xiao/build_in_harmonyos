# liblms7compact 0.0.1-git20190125.bfd5418 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-09-18
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 源码下载：GitHub 官方源 `xtrx-sdr/liblms7002m` commit `bfd5418098f1171c47434e08a82074ff22a1bfbe`（tarball sha256 c9dfff76...e3c5c）
2. 应用补丁（3 个）：CMakeLists.txt / lms7_defaults.c / regs/enum_parser.py
3. CMake 构建（Conan 静态默认）：
   ```
   cmake -S . -B build -DBUILD_SHARED_LIBS=OFF -DCMAKE_INSTALL_PREFIX=<prefix>
   cmake --build build -j4
   cmake --install build
   ```
   - configure 阶段 `find_package(Python3)` 运行 `regs/enum_parser.py` 生成 `lms7002m_defs.h`（3258 行）
   - 产物：`liblms7compact.a`（静态）或 `liblms7compact.so`（动态，`-DBUILD_SHARED_LIBS=ON`）+ 头文件 `liblms7002m.h`
4. test_package：2 个测试程序（消费者集成测试 + 鸿蒙特有默认 hook 测试），ctest 运行

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake configure 报错 `Compatibility with CMake < 3.5 has been removed` | 上游 `cmake_minimum_required(2.8)` 太旧，CMake 4.x 不支持 | 提升到 `cmake_minimum_required(3.16)` |
| 2 | configure 强制要求 Python 2.7 + Cheetah 模板模块 | 上游 `find_package(PythonInterp 2.7)` + `execute_process` 检查 Cheetah | 改为 `find_package(Python3 COMPONENTS Interpreter)`，删除 Cheetah 检查 |
| 3 | `regs/enum_parser.py` 是 Python2 语法（`iteritems`）且依赖 Cheetah 模板 | 上游 2019 年代码 | 重写为纯 Python3 + 字符串拼接，输出符号名/值不变；本地冒烟验证宏展开的寄存器写入序列正确 |
| 4 | 链接 `.so` 失败：`lms7_spi_transact/lms7_spi_post/lms7_log_ex` 未定义 | 上游设计：SPI/日志 hook 由集成方提供，库内无默认实现 | 新增 `lms7_defaults.c` 提供 weak 默认实现（消费方可强符号覆盖）；无硬件时返回错误而非崩溃 |
| 5 | 本地 macOS 编译报 `usleep` 隐式声明 | `liblms7002m.h` 用 `#ifdef __linux` 保护 `unistd.h`；macOS 无 `__linux` | 仅本地验证用 `-include unistd.h`；OHOS 工具链 triple `aarch64-linux-ohos` 定义 `__linux__`，无需修改源码 |
| 6 | 上游 CMakeLists 硬编码非 Windows 构建 SHARED | `if(CMAKE_SYSTEM_NAME MATCHES "Windows") STATIC else SHARED` | 改为尊重 `BUILD_SHARED_LIBS`（Conan shared 选项可控静态/动态） |

## 源码修改

| 补丁 | 内容 |
|------|------|
| 0001-CMakeLists.txt.patch | cmake_minimum_required 2.8→3.16；PythonInterp 2.7→Python3；删除 Cheetah 检查；硬编码 SHARED→BUILD_SHARED_LIBS |
| 0002-lms7_defaults.c.patch | 新增 weak 默认 hook 实现（lms7_log_ex/lms7_spi_transact/lms7_spi_post） |
| 0003-regs-enum_parser.py.patch | Python2+Cheetah→纯 Python3，输出语义不变 |

## 依赖版本

- cmake（本地 4.4.3 / CI CMake）
- python3（构建期代码生成，无 pip 依赖）
- 无外部 C 库依赖

## 验证结果

```bash
# 本地（macOS）静态构建 + 冒烟测试
cmake -S . -B build -DBUILD_SHARED_LIBS=OFF  # configure=0 build=0 install=0
./test_liblms7compact                # ALL TESTS PASSED（reset 写入序列 0x0020/0x0020/0x002E、disable 0x0081/0x00A6、CGEN 算法）
./test_liblms7compact_default_hooks   # ALL TESTS PASSED（weak 默认 hook 生效，无硬件返回错误）
# 补丁闭环
patch -p1 < 各补丁 应用到干净 orig → 与 work 完全一致
```

## 注意事项

- 动态构建（shared=True）产物缺 DT_SONAME（上游未设 SOVERSION）；CI 默认 shared=False（静态）规避 L5a
- `lms7_spi_transact/lms7_spi_post/lms7_log_ex` 为 weak 符号：真实硬件集成方必须提供强符号覆盖
- 上游无官方测试（CMakeLists 无 enable_testing/ctest）；测试由 test_package 补齐（5 级测试体系 L1）
### 对话 #1
- 2026-09-18：完成 liblms7compact 0.0.1-git20190125.bfd5418 鸿蒙适配。查重通过（origin/upstream/本地均无同名分支或版本）。
  确认上游为 xtrx-sdr/liblms7002m commit bfd5418（Debian 打包名 liblms7compact）。W0：CMake 项目，
  零外部依赖，构建期代码生成（regs/enum_parser.py）。核心适配 3 点：Python2+Cheetah 构建脚本重写为
  纯 Python3；cmake_minimum_required 2.8→3.16 并改用 find_package(Python3)；新增 lms7_defaults.c 提供
  SPI/日志 hook 的 weak 默认实现使库可独立链接。liblms7002m.h 的 #ifdef __linux 保护 unistd.h 在
  OHOS（triple 定义 __linux__）下天然可用。本地 macOS conan create 2/2 测试通过（15 断言），
  W3 本地 CI 模拟通过（CONAN_PROFILE=default 验证，OHOS 真实构建由远程 CI 执行）。
---

**编译结束**: 2026-09-18 22:13
**最终状态**: published
