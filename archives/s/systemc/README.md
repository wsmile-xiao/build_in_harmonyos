# SystemC — 系统级硬件描述与仿真库

## 简介

SystemC 是由 Accellera Systems Initiative 维护的开放标准 C++ 系统级硬件描述与仿真库。
它提供了一套基于 C++ 的类库和仿真内核，用于建模、仿真和验证电子系统设计。

SystemC 广泛应用于：
- 电子系统级（ESL）设计与验证
- 硬件/软件协同仿真
- 事务级建模（TLM）
- 架构探索与性能分析

## 核心功能

- **模块化设计**：`sc_module` 支持层次化建模，可嵌套组合复杂系统
- **信号与端口**：`sc_signal`、`sc_in`、`sc_out` 实现模块间数据通信
- **进程模型**：`SC_METHOD`（方法进程）、`SC_THREAD`（线程进程）、`SC_CTHREAD`（时钟线程）
- **事件驱动仿真**：`sc_event`、`sc_event_queue` 精确时序控制
- **FIFO通道**：`sc_fifo` 支持阻塞式进程间通信
- **波形跟踪**：VCD/WIF 格式波形输出，可配合 GTKWave 等工具查看
- **事务级建模**：TLM 2.0 标准支持，简化高层抽象建模
- **数据类型**：`sc_int`、`sc_uint`、`sc_bigint`、`sc_bv`、`sc_lv`、`sc_fixed` 等

## 版本信息

- **版本**：3.0.2（2025年10月31日发布）
- **TLM版本**：2.0.6
- **语言标准**：要求 C++17 或以上
- **许可证**：Apache 2.0（包含部分 Boost 和 QuickThreads 代码）

## 鸿蒙平台编译信息

- **构建系统**：CMake
- **编译器**：clang/clang++ 15.0.4
- **平台**：HarmonyOS (HongMeng Kernel 1.12.0, aarch64)
- **编译日期**：2026-05-27
- **编译状态**：published

### 编译命令

```bash
cd $BUILD_SRC_DIR
mkdir build && cd build
cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_BUILD_TYPE=Release
make -j1
make install DESTDIR=$TEST_PREFIX
```

### 使用方式

```bash
# 编译 SystemC 程序需要 C++17 支持
clang++ -std=c++17 -I$DEFAULT_PREFIX/include -L$DEFAULT_PREFIX/lib -lsystemc your_app.cpp -o your_app

# 运行时需要设置 LD_LIBRARY_PATH
LD_LIBRARY_PATH=$DEFAULT_PREFIX/lib ./your_app
```

### 安装产物

| 目录 | 内容 |
|------|------|
| `lib/` | `libsystemc.so`（共享库） |
| `include/` | `systemc.h`、`tlm.h`、`sysc/`（内核头文件）、`tlm_core/`（TLM头文件） |
| `lib/cmake/` | `SystemCLanguage/`、`SystemCTLM/`（CMake find_package 配置） |
| `share/doc/` | 文档、LICENSE、README |

## 功能验证

在鸿蒙平台上执行了5组真实功能测试，全部通过：

| 测试 | 功能点 | 结果 |
|------|--------|------|
| Test1 | sc_signal + sc_module + SC_METHOD | ✅ PASS |
| Test2 | SC_THREAD + sc_wait + 时钟驱动 | ✅ PASS |
| Test3 | sc_fifo 阻塞式读写 | ✅ PASS |
| Test4 | 端口连接 + 数据类型运算 | ✅ PASS |
| Test5 | VCD波形跟踪文件生成 | ✅ PASS |

## 注意事项

1. SystemC 3.0.2 要求 C++17，编译时必须添加 `-std=c++17`
2. SystemC 是纯库（无可执行命令），属于库类型软件包
3. 运行时需设置 `LD_LIBRARY_PATH` 或使用 CMake `find_package(SystemCLanguage)` 自动链接
4. CMake 自动检测平台为 `harmonyos`，`SystemC_TARGET_ARCH=harmonyos`
5. VCD 跟踪 API 有变化：`sc_vcd_trace_file` → `sc_trace_file`（3.0.2）

## 源码

- **URL**：https://github.com/accellera-official/systemc/archive/refs/tags/3.0.2.tar.gz
- **无补丁**：SystemC 3.0.2 CMake 构建在鸿蒙上原生兼容，无需修改源码