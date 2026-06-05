# glfw 3.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-19
- 编译器: clang/clang++
- 状态: published

## 编译步骤

1. 下载源码（从 GitHub）：
   ```bash
   curl -L "https://github.com/glfw/glfw/archive/refs/tags/3.4.tar.gz" -o ~/tmp/glfw-3.4.tar.gz
   ```

2. 初始化编译环境：
   ```bash
   python3 ohc-run.py init-build glfw 3.4 --url=file://~/tmp/glfw-3.4.tar.gz
   ```

3. CMake 配置（需要添加 `_GNU_SOURCE` 宏）：
   ```bash
   mkdir build && cd build
   cmake .. -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX -DCMAKE_C_FLAGS="-D_GNU_SOURCE"
   ```

4. 编译：
   ```bash
   make -j2
   ```

5. 安装到 staging 目录：
   ```bash
   make install DESTDIR=$TEST_PREFIX
   ```

6. 验证和打包：
   ```bash
   python3 ohc-run.py verify-build glfw 3.4
   python3 ohc-run.py package glfw 3.4
   ```

7. 本地安装：
   ```bash
   make install
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CLOCK_REALTIME/CLOCK_MONOTONIC 未定义 | musl libc 需要特定的特性宏来启用 POSIX 定时器常量 | 添加 `#include <time.h>` 到 `src/posix_time.c` + 设置 `-DCMAKE_C_FLAGS="-D_GNU_SOURCE"` |

## 源码修改

### src/posix_time.c
添加 `#include <time.h>` 头文件包含：
```c
#include "internal.h"

#if defined(GLFW_BUILD_POSIX_TIMER)

#include <unistd.h>
#include <sys/time.h>
#include <time.h>  // 新增：启用 clock_gettime 和 CLOCK_* 常量
```

**修改原因**：
- HarmonyOS/musl libc 的 time.h 中定义了 `clock_gettime` 函数和 `CLOCK_REALTIME=0`、`CLOCK_MONOTONIC=1` 常量
- 需要显式包含 time.h 并添加 `_GNU_SOURCE` 宏才能正确编译
- 这是 musl libc 与 glibc 的行为差异

## 依赖版本

- CMake 4.1.2
- clang 15.0.4
- POSIX 线程库（libpthread）

## 验证结果

```bash
# 库文件验证
ls -lh ~/usr/local/lib/libglfw3.a
# 输出: 231K 静态库文件

# 头文件验证
ls -lh ~/usr/local/include/GLFW/
# 输出: glfw3.h (236K), glfw3native.h (21K)

# 质量门禁
python3 ohc-run.py verify-build glfw 3.4
# 结果: PASS (G1-G4 全部通过)
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| glfw-3.4-ohos-aarch64.tar.gz | 507KB | 预编译包（静态库 + 头文件 + cmake 配置） |

## 注意事项

1. **构建系统类型**：GLFW 使用 CMake 构建，不是 autotools。需要设置正确的构建系统参数。
2. **CMake 平台检测**：CMake 会检测到 HarmonyOS 并提示"System is unknown to cmake"，但这不影响编译。
3. **静态库编译**：GLFW 默认编译为静态库 `libglfw3.a`，无共享库版本。
4. **无 GUI 后端**：当前编译仅包含基础功能，无实际图形界面支持（需要后续适配 Wayland/X11/Win32 等）。
5. **测试程序**：GLFW 提供了丰富的测试程序（build/tests/ 目录），但运行需要图形系统支持。
**预编译包**: archives/g/glfw/3.4/packaging/glfw-3.4-ohos-aarch64.tar.gz
---

**编译结束**: 2026-05-19 14:58
**最终状态**: built
