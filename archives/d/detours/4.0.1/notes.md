# detours 4.0.1 适配笔记

## 编译环境
- 构建系统: cmake
- 编译日期: 2026-07-29
- 编译器: clang/clang++
- 状态: built

## 编译步骤

1. 下载上游源码 v4.0.1 并解压
2. 应用 `ohos-compat.patch` 补丁（CMake 构建系统 + Windows API 兼容层 + C++ 标准合规修复）
3. 使用 CMake 交叉编译：
   ```bash
   cmake -DCMAKE_SYSTEM_NAME=Linux -DCMAKE_SYSTEM_PROCESSOR=aarch64 \
         -DBUILD_SHARED_LIBS=OFF ..
   make -j2
   make install
   ```

## 遇到的问题与解决方案

| # | 问题 | 根因 | 解决方案 |
|---|------|------|----------|
| 1 | 上游使用 NMAKE 构建系统，不兼容鸿蒙 | NMAKE 是 Windows 专有工具 | 通过补丁添加 CMakeLists.txt 替代 NMAKE |
| 2 | Windows API 头文件缺失 | Detours 依赖 Windows API（CreateProcess、VirtualMemory 等） | 补丁中添加兼容性头文件，提供必要宏和类型定义 |
| 3 | C++ 标准合规问题 | creatwth.cpp、detours.cpp、image.cpp 中的旧式 C++ 写法 | 补丁修复为标准 C++ 写法 |

## 源码修改

- **ohos-compat.patch**（1476行）：修改 creatwth.cpp、detours.cpp、detours.h、image.cpp 四个文件
  - 添加 CMakeLists.txt 构建配方
  - 添加 Windows API 兼容层（wtypes.h 兼容、内存常量定义等）
  - 修复 C++ 标准合规问题

## 依赖版本

无外部依赖，纯静态库。

## 验证结果

```bash
# conan create 验证
conan create archives/d/detours/4.0.1/conanfile.py --build=missing
# 产物检查
readelf -h libdetours.a  # ELF 64-bit, aarch64
```

## 交付物

| 文件 | 大小 | 说明 |
|------|------|------|
| libdetours.a | ~300KB | 静态库，aarch64 ELF |

## 注意事项

### R40 适配完整性声明

**适配范围：仅链接支持（link_only）**

- Detours 核心功能（函数拦截/hooking）依赖 Windows PE 格式操作、进程/线程管理等 Windows 内部机制，在 HarmonyOS 上**完全不可用**
- 本适配仅提供编译链接层面的兼容（Windows API 兼容头文件 + CMake 构建系统），不提供任何运行时拦截能力
- test_package 验证库链接成功（DetourIsHelperProcess 调用），**非功能验证**
- 下游消费者链接此库后，调用 DetourAttach/DetourTransactionBegin 等拦截 API 将静默返回 stub 值或行为异常
- **下游消费者不应依赖此库的拦截功能**，如需函数拦截能力，需基于鸿蒙平台实现（如 ELF PLT/GOT hook、inline hook 等）
---

**编译结束**: 2026-07-29 20:53
**最终状态**: built
