# libucontext

libucontext is a library which provides the `ucontext.h` C API. Unlike other implementations, it faithfully follows the kernel process ABI when doing context swaps.

## 功能概述

- 提供 POSIX ucontext API（getcontext, setcontext, swapcontext, makecontext）
- 支持多种架构（aarch64, arm, x86, x86_64, riscv64 等）
- 提供 glibc 兼容的 ABI
- 支持 freestanding 模式（用于裸机环境）
- 提供 libucontext_posix 库（包含信号屏蔽处理）

## OHOS 适配要点

- aarch64 架构为 tier 1 支持，无需修改
- 使用 Makefile 构建，通过参数控制：
  - ARCH: 架构类型（自动检测或手动指定）
  - LIBDIR: 库安装路径
  - INCLUDEDIR: 头文件安装路径
  - PKGCONFIGDIR: pkg-config 文件路径
  - DESTDIR: staging 安装路径
- 编译命令示例：
  ```bash
  make ARCH=aarch64 LIBDIR=/path/to/lib INCLUDEDIR=/path/to/include
  make install DESTDIR=/staging/path
  ```
- 测试套件完整，可通过 make check 验证

## 依赖关系

- 编译依赖：无（纯汇编和 C 实现）
- 运行依赖：无（静态库可独立使用，动态库需标准 C 库）

## 参考资料

- 官方仓库：https://github.com/kaniini/libucontext
- 版本：v1.2
- 许可证：ISC