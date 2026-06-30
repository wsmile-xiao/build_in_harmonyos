# aom (AV1 Codec Library)

## 简介

aom 是 Alliance for Open Media 开发的 AV1 视频编解码器库，提供高质量的 AV1 编码和解码功能。

## 版本信息

- 当前版本: 3.9.1
- 发布日期: 2024-06-06
- 官方仓库: https://aomedia.googlesource.com/aom

## HarmonyOS 适配状态

- 编译状态: ✅ published
- 编译日期: 2026-05-21
- 编译器: clang 15.0.4
- 构建系统: cmake

## 编译配置

- 目标平台: HarmonyOS (aarch64)
- 禁用汇编优化: AOM_TARGET_CPU=generic
- 编译类型: Release
- 组件配置:
  - ENABLE_TESTS=OFF
  - ENABLE_EXAMPLES=OFF
  - ENABLE_DOCS=OFF

## 预编译包

### Release 静态库版本
- 文件: aom-3.9.1-ohos-aarch64.tar.gz
- 大小: 6.1M
- 内容:
  - libaom.a (静态库，Release 编译)
  - 头文件 (aom/*.h)
  - pkg-config 文件 (aom.pc)

### Debug 静态库版本
- 文件: aom-3.9.1-ohos-aarch64-debug.tar.gz
- 大小: 26M
- 内容:
  - libaom.a (静态库，Debug 编译，含调试符号)
  - 头文件 (aom/*.h)
  - pkg-config 文件 (aom.pc)

### Release 动态库版本（可选）
- 文件: aom-3.9.1-ohos-aarch64-shared.tar.gz
- 大小: 11M
- 内容:
  - libaom.so.3.9.1 (动态库)
  - libaom.so.3 (符号链接)
  - libaom.so (符号链接)
  - libaom.a (静态库)
  - 头文件 (aom/*.h)
  - pkg-config 文件 (aom.pc)

## 使用说明

### 安装

使用 cmd-pkgs 公共安装脚本安装预编译包：

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- aom 3.9.1
```

### 使用

编译时链接 aom 库：

```bash
# 静态链接
clang -o myapp myapp.c -laom -lm

# 动态链接
clang -o myapp myapp.c -laom -lm
```

或使用 pkg-config：

```bash
clang -o myapp myapp.c $(pkg-config --cflags --libs aom)
```

## 技术特性

- 支持 AV1 编码和解码
- 高性能编解码算法
- 多线程支持
- 多种编码模式（实时、单pass、twopass）
- 支持 SVC（可伸缩视频编码）

## 已知限制

1. 汇编优化已禁用（使用 generic CPU 模式）
2. CMake 不支持原生 HarmonyOS 平台（使用 Linux 作为 workaround）
3. 动态库版本需要额外的依赖管理

## 编译笔记

详细的编译过程和问题解决方案见 `3.9.1/notes.md`。

## 许可证

BSD 2-Clause License + AOM Patent License 1.0

## 参考链接

- 官方文档: https://aomedia.googlesource.com/aom/+/main/README.md
- AV1 规范: https://aomedia.github.io/av1-spec/