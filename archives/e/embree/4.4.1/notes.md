# embree 4.4.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-09
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 初始化编译环境：
   ```bash
   python3 $SKILL_ROOT/scripts/ohc-run.py init-build embree 4.4.1 --url=https://github.com/RenderKit/embree/archive/refs/tags/v4.4.1.tar.gz
   ```

2. CMake 配置（ARM NEON 架构）：
   ```bash
   cmake -B build \
     -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
     -DCMAKE_BUILD_TYPE=Release \
     -DEMBREE_TASKING_SYSTEM=INTERNAL \
     -DEMBREE_TUTORIALS=OFF \
     -DEMBREE_ARM=ON \
     -DEMBREE_ISA_NEON=ON \
     -DEMBREE_ISA_NEON2X=OFF \
     -DEMBREE_ISA_SSE2=OFF \
     -DEMBREE_ISA_SSE42=OFF \
     -DEMBREE_ISA_AVX=OFF \
     -DEMBREE_ISA_AVX2=OFF \
     -DEMBREE_STATIC_LIB=ON
   ```

3. 编译和安装：
   ```bash
   cmake --build build -j2
   DESTDIR=$TEST_PREFIX cmake --install build
   cmake --install build  # 安装到 ~/usr/local
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | cmake 缺少 TBB | 默认使用 TBB tasking system | 使用 `-DEMBREE_TASKING_SYSTEM=INTERNAL` 避免依赖 |
| 2 | glfw 不支持 HarmonyOS | tutorials 需要 glfw | 禁用 tutorials：`-DEMBREE_TUTORIALS=OFF` |
| 3 | pthread_getaffinity_np 未定义 | HarmonyOS 不支持此函数 | 添加 `__OHOS__` 宏，使用 `sysconf(_SC_NPROCESSORS_ONLN)` |
| 4 | pthread_setaffinity_np 未定义 | HarmonyOS 使用 sched_setaffinity | 添加 `__OHOS__` 宏，使用 `sched_setaffinity(pthread_gettid_np(*tid), ...)` |
| 5 | pthread_cancel 未定义 | HarmonyOS 不支持 | 添加 `__OHOS__` 宏，与 Android 一样禁用线程销毁 |
| 6 | 编译 AVX2 代码失败 | CMake 未识别 ARM 架构 | 明确设置 `-DEMBREE_ARM=ON` 并禁用 x86 ISA |
| 7 | 链接 libc++ 失败 | 动态库链接问题 | 使用静态库：`-DEMBREE_STATIC_LIB=ON` |

## 源码修改

### common/sys/sysinfo.cpp
- 添加 `__OHOS__` 平台识别（HarmonyOS 32bit/64bit）
- 在 `getNumberOfLogicalThreads` 中添加 `__OHOS__` 分支，使用 `sysconf(_SC_NPROCESSORS_ONLN)`
  替代 `pthread_getaffinity_np`

### common/sys/thread.cpp
- 将 Linux 平台条件改为 `__LINUX__ && !__ANDROID__ && !__OHOS__`
- 将 Android/HarmonyOS 平台合并为 `__ANDROID__ || __OHOS__`
- 使用 `sched_setaffinity(pthread_gettid_np(*tid), ...)` 替代 `pthread_setaffinity_np`
- 禁用 `pthread_cancel`（与 Android 相同）

## 依赖版本

- 无外部依赖（使用 INTERNAL tasking system）
- pthread: 系统库

## 验证结果

```bash
# 验证库文件
ls -lh ~/usr/local/lib/libembree4.a
# 输出：14M static library

# 验证头文件
ls ~/usr/local/include/embree4/rtcore.h
# 输出：存在
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| embree-4.4.1-ohos-aarch64.tar.gz | 18585KB | 预编译包（静态库） |
| libembree4.a | 14M | 主库文件 |
| libsys.a, libmath.a, libsimd.a, liblexers.a, libtasking.a | 各约 1MB | 辅助库 |

## 注意事项

1. **必须使用静态库**：动态库在 HarmonyOS 上有 libc++ 链接问题，建议使用静态库
2. **ISA 配置**：必须明确设置 `EMBREE_ARM=ON` 和 `EMBREE_ISA_NEON=ON`，否则会尝试编译 x86 SSE/AVX 代码
3. **无 tutorials**：glfw 不支持 HarmonyOS，必须禁用 tutorials
4. **无测试**：测试套可能需要运行环境，跳过测试（test_integration 和 test_package 目标）
5. **无可执行文件**：embree 是纯库，没有命令行工具
---

**编译结束**: 2026-08-06 09:17
**最终状态**: built
