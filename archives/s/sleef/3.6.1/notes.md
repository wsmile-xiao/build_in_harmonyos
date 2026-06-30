# sleef 3.6.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-06-17
- 编译器: clang/clang++
- 状态: built

## 编译步骤

### Step 1: 初始化
```bash
python3 $SKILL_ROOT/scripts/ohc-run.py init-build sleef 3.6.1 \
  --url=https://github.com/shibatch/sleef/archive/refs/tags/3.6.1.tar.gz
```

### Step 2: CMake Configure
```bash
cd ~/tmp/builds/sleef-3.6.1.work/build
cmake -DCMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX \
      -DCMAKE_BUILD_TYPE=Release \
      -DSLEEF_BUILD_TESTS=OFF ..
```

### Step 3: Make
```bash
make -j1
```

**结果**: 成功（编译完成）

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | CMake 无法识别平台 | HarmonyOS 未在 CMake 平台列表中 | 使用 `uname -m` 检测处理器架构 |
| 2 | 生成的代码缺少函数声明 | CMAKE_SYSTEM_PROCESSOR=unknown | 添加平台检测补丁 |

## 根因分析

SLEEF 使用 CMake 的代码生成机制：
1. `mkrename` 工具生成头文件
2. `mkdisp` 工具生成调度代码
3. 生成的代码依赖平台检测结果

**问题**: 在 HarmonyOS 平台上，CMake 输出 "System is unknown to cmake"，导致生成的代码中缺少必要的函数声明。

**解决方案**: 在 Configure.cmake 中添加平台检测逻辑：
```cmake
if(NOT SLEEF_TARGET_PROCESSOR OR SLEEF_TARGET_PROCESSOR STREQUAL "unknown")
  execute_process(
    COMMAND uname -m
    OUTPUT_VARIABLE UNAME_PROCESSOR
    OUTPUT_STRIP_TRAILING_WHITESPACE
  )
  if(UNAME_PROCESSOR)
    set(SLEEF_TARGET_PROCESSOR "${UNAME_PROCESSOR}")
    message(STATUS "Detected processor via uname: ${SLEEF_TARGET_PROCESSOR} (HarmonyOS)")
  endif()
endif()
```

## 源码修改

修改文件: Configure.cmake
修改位置: 第100行后添加12行平台检测逻辑

## 依赖版本

- cmake: 4.1.2
- clang: 15.0.4

## 验证结果

编译成功，生成静态库文件：
- libsleef.a (1.4MB)
- libsleefgnuabi.a (375KB)
- SVE 支持已启用
- NEON 支持已启用

## 交付物

- 预编译包: sleef-3.6.1-ohos-aarch64.tar.gz (1.9MB)
- 补丁文件: 0001-Configure.cmake.patch

## 注意事项

1. **平台检测问题**: 通过 uname -m 绕过 CMake 平台检测限制
2. **SVE 支持**: 成功启用 ARM Scalable Vector Extension
3. **适用范围**: 此补丁策略适用于其他 CMake 无法识别的类 Unix 平台

---

**编译结束**: 2026-06-17 14:55
**最终状态**: built