# patchelf

## 简介

patchelf 是一个用于修改现有 ELF 可执行文件和共享库的工具，由 NixOS 项目开发。

## 主要功能

- **修改 RPATH/RUNPATH**: 改变可执行文件或库的运行时库搜索路径
- **修改 SONAME**: 改变共享库的名称标识
- **添加/删除依赖库**: 动态添加或删除 NEEDED 条目
- **设置解释器**: 改变可执行文件的动态链接器路径

## 适用场景

- 软件打包和分发（修改依赖路径）
- 容器化应用（调整库路径）
- 跨平台部署（适配不同环境）

## 版本列表

| 版本 | 状态 | 发布日期 | 预编译包 |
|------|------|----------|----------|
| 0.18.0 | published | 2026-05-20 | ✅ patchelf-0.18.0-ohos-aarch64.tar.gz (365KB) |

## 安装方法

### 方法 1: 使用 cmd-pkgs 安装脚本（推荐）

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- patchelf 0.18.0
```

### 方法 2: 手动安装

```bash
# 下载预编译包
wget https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/patchelf-0.18.0-ohos-aarch64.tar.gz

# 解压到目标目录
tar xzf patchelf-0.18.0-ohos-aarch64.tar.gz -C /data/data/com.example.hmsvc/usr/local
```

## 使用示例

### 查看当前 RPATH

```bash
patchelf --print-rpath /path/to/binary
# 输出: $ORIGIN/../lib:/usr/lib
```

### 设置新的 RPATH

```bash
patchelf --set-rpath /new/library/path /path/to/binary
```

### 查看依赖库列表

```bash
patchelf --print-needed /path/to/binary
# 输出: libc.so.6
# 输出: libm.so.6
```

### 添加依赖库

```bash
patchelf --add-needed libnew.so /path/to/binary
```

### 移除依赖库

```bash
patchelf --remove-needed libold.so /path/to/binary
```

### 修改 SONAME（共享库）

```bash
patchelf --set-soname libnewname.so /path/to/library.so
```

## 技术说明

### 构建系统

- 构建工具: autotools (configure + make)
- 编译器: clang 15.0.4 (OHOS)
- 平台: OpenHarmony (aarch64)

### 补丁说明

版本 0.18.0 包含 4 个 autotools 模板文件补丁：
- 0001-Makefile.in.patch: 顶层构建规则
- 0002-src-Makefile.in.patch: src 目录构建规则
- 0003-tests-Makefile.in.patch: 测试构建规则
- 0004-aclocal.m4.patch: autoconf 宏文件

这些补丁修改的是 autotools 的输入模板文件，用于适配平台构建系统。

### 依赖关系

patchelf 是独立工具，无外部依赖。

## 注意事项

1. **备份重要文件**: 使用 patchelf 修改二进制文件前建议备份原文件
2. **权限要求**: 需要对目标文件有写权限
3. **ELF 格式**: 只支持 ELF 格式文件（不支持 Windows PE 或 macOS Mach-O）
4. **测试验证**: 修改后建议测试文件是否正常运行

## 常见问题

### Q: patchelf 修改后文件无法执行？

A: 检查 RPATH 设置是否正确，确保依赖库在指定路径中可找到。

### Q: 可以多次修改同一个文件吗？

A: 可以，但建议每次修改前备份，避免累积错误。

### Q: patchelf 支持 32 位和 64 位吗？

A: 支持，patchelf 可以处理 32 位和 64 位 ELF 文件。

## 参考链接

- 官方仓库: https://github.com/NixOS/patchelf
- 官方文档: https://github.com/NixOS/patchelf/blob/master/README.md
- cmd-pkgs 仓库: https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs

---

最后更新: 2026-05-21