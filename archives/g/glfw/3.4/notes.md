# glfw 3.4 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-05-27
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. **下载源码**
   ```bash
   wget https://github.com/glfw/glfw/releases/download/3.4/glfw-3.4.zip
   ```

2. **设置环境**
   ```bash
   export LD_LIBRARY_PATH="/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/llvm/lib:/storage/Users/currentUser/usr/local/lib"
   export OHOS_SYSROOT="/data/service/hnp/ohos-sdk.org/ohos-sdk_26.0.0.18/ohos/native/sysroot"
   ```

3. **CMake 配置**
   ```bash
   cmake \
     -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
     -DCMAKE_BUILD_TYPE=Release \
     -DCMAKE_C_FLAGS="-isystem $OHOS_SYSROOT/usr/include -D_GNU_SOURCE" \
     -DGLFW_BUILD_X11=OFF \
     -DGLFW_BUILD_WAYLAND=OFF \
     -DGLFW_BUILD_EXAMPLES=OFF \
     -DGLFW_BUILD_TESTS=OFF \
     -DGLFW_BUILD_DOCS=OFF \
     -DBUILD_SHARED_LIBS=OFF \
     ..
   ```

4. **编译**
   ```bash
   make -j2
   ```

5. **安装**
   ```bash
   make install DESTDIR=$TEST_PREFIX  # staging
   make install                       # local
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | lld 链接器报 "Error loading shared library libxml2.so.16" | OHOS SDK 的 lld 依赖 libxml2.so.16，但 LD_LIBRARY_PATH 未包含 SDK 路径 | 设置 LD_LIBRARY_PATH 包含 `/data/service/hnp/ohos-sdk.org/ohos-sdk_*/ohos/native/llvm/lib` |
| 2 | CLOCK_REALTIME/CLOCK_MONOTONIC undeclared identifier | musl libc 中 CLOCK_* 常量需要 POSIX 扩展宏启用 | 添加 `-D_GNU_SOURCE` 编译选项 |
| 3 | GLFW 不支持 X11/Wayland | OpenHarmony 无 X11/Wayland | 禁用 X11/Wayland，只构建 Null platform |

## 源码修改

**文件: src/posix_time.c**
- 添加 `#include <time.h>` 头文件（第 27 行）
- 实际问题通过编译选项 `-D_GNU_SOURCE` 解决

补丁: `0001-src-posix_time.c.patch`

## 依赖版本

无外部依赖（纯 C 库静态链接）

## 验证结果

```bash
# 验证静态库
llvm-ar t ~/usr/local/lib/libglfw3.a
# 输出: context.c.obj init.c.obj input.c.obj ... (17 个对象文件)

# 验证头文件
ls ~/usr/local/include/GLFW/
# 输出: glfw3.h glfw3native.h
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libglfw3.a | 150KB | 静态库（Null platform） |
| glfw3.h | 242KB | 主头文件 |
| glfw3native.h | 21KB | 平台原生接口头文件 |
| glfw3.pc | - | pkg-config 文件 |
| cmake/glfw3/* | - | CMake 配置文件 |

## 注意事项

1. GLFW 3.4 在 OpenHarmony 上只支持 Null platform，无实际窗口功能
2. Null platform 主要用于测试和开发，不能创建真实窗口
3. 编译时必须添加 `-D_GNU_SOURCE` 以启用 POSIX 时钟定义
4. 源码是 zip 格式，不是 tar.gz

## 知识提取

- E103: OHOS SDK lld libxml2 问题
- E104: POSIX 时钟常量需要 _GNU_SOURCE
- E105: GLFW Null platform 配置
---

**编译结束**: 2026-05-27 12:12
**最终状态**: built
