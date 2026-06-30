# Clipper2 2.0.1 编译笔记

## 编译日期
2026-06-15

## 源码获取
- 使用 git clone 从 GitHub 获取源码
- 标签：Clipper2_2.0.1

## 编译环境
- 系统：OpenHarmony (HarmonyOS)
- 编译器：Clang 15.0.4
- CMake 版本：3.15+
- C++ 标准：17

## 编译选项
- `CMAKE_INSTALL_PREFIX=$DEFAULT_PREFIX`（~/usr/local）
- `CLIPPER2_EXAMPLES=OFF`（禁用示例以加快编译）
- `CLIPPER2_TESTS=OFF`（禁用测试以加快编译）
- `CLIPPER2_UTILS=OFF`（禁用工具）
- `BUILD_SHARED_LIBS=ON`（构建共享库）

## 编译产物
- libClipper2.so（主库）
- libClipper2Z.so（支持 USINGZ 的变体库）
- 头文件：include/clipper2/*.h
- pkg-config 文件：lib/pkgconfig/Clipper2.pc, Clipper2Z.pc
- CMake 配置文件：lib/cmake/clipper2/*.cmake

## 特殊处理
- CMake 提示 "System is unknown to cmake"，但不影响编译
- 使用 jobserver 时出现 mkfifo 权限警告，但不影响编译结果
- DESTDIR 模式安装时路径使用绝对路径，导致路径层级较深，但不影响打包

## 无依赖
Clipper2 是无外部依赖的库，仅依赖标准库（libc.so）

## 编译状态
✅ 编译成功
✅ 安装成功
✅ 本地验证通过

## 后续步骤
- 创建预编译包
- 运行质量门禁检查
- 发布到 cmd-pkgs

---
**编译结束**: 2026-06-15 14:32
**最终状态**: built
---

**编译结束**: 2026-06-15 14:35
**最终状态**: built
