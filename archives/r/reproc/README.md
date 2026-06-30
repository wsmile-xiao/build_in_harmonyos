# reproc

## 简介

reproc 是一个跨平台的进程管理 C 库，提供了简化的进程创建、管道管理、输入输出重定向等功能。

- **作者**: DaanDeMeyer
- **许可证**: MIT
- **主页**: https://github.com/DaanDeMeyer/reproc

## 功能特性

- 进程创建和管理
- 标准输入/输出/错误流的重定向
- 进程生命周期管理（启动、等待、终止）
- 跨平台支持（Linux、macOS、Windows）
- 提供 C 和 C++ 绑定

## 已编译版本

| 版本 | 状态 | 编译日期 | 构建系统 |
|------|------|----------|----------|
| 14.2.5 | built | 2026-05-20 | cmake |

## 使用方法

### 通过 pkg-config 编译

```bash
export PKG_CONFIG_PATH=$HOME/usr/local/lib/pkgconfig:$PKG_CONFIG_PATH

# 编译 C 程序
clang your_program.c $(pkg-config --cflags --libs reproc) -o your_program

# 查看版本
pkg-config --modversion reproc
```

### 通过 CMake 使用

```cmake
find_package(reproc REQUIRED)
target_link_libraries(your_target PRIVATE reproc)
```

### 头文件位置

```
$HOME/usr/local/include/reproc/
  - drain.h      # 数据流处理函数
  - export.h     # 导出宏定义
  - reproc.h     # 核心进程管理 API
  - run.h        # 简化的进程运行函数
```

### 库文件位置

```
$HOME/usr/local/lib/libreproc.a  # 静态库（53KB）
```

## API 示例

### 基本进程执行

```c
#include <reproc/run.h>

int result = reproc_run("echo", (const char *[]) { "echo", "Hello", NULL });
```

### 进程管理

```c
#include <reproc/reproc.h>

reproc_t *process = reproc_new();
reproc_start(process, (const char *[]) { "ls", "-la", NULL });
reproc_wait(process, REPROC_INFINITE);
reproc_destroy(process);
```

## 依赖

reproc 是独立库，无外部依赖（除标准 C 库外）。

## 注意事项

- reproc 是纯静态库，无可执行文件
- pkg-config 版本号可能显示为 14.2.4（与源码版本一致）
- 测试套件需要启用 `REPROC_TEST=ON` cmake 选项
- 在鸿蒙平台上使用 `-pthread` 编译选项（CMake 自动添加）

## 文档资源

- 官方 README: https://github.com/DaanDeMeyer/reproc#readme
- API 文档: https://github.com/DaanDeMeyer/reproc/blob/main/README.md
- 示例代码: https://github.com/DaanDeMeyer/reproc/tree/main/examples

## 版本历史

- **14.2.5**: 2024-03-26 - 稳定版本，鸿蒙平台编译通过