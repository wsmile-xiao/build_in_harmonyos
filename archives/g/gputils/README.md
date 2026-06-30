# gputils - GNU PIC Utilities

## 简介

gputils 是 GNU PIC Utilities 的简称，是一套用于 PIC 微控制器开发的开源工具集。
该工具集提供了汇编器、链接器、反汇编器等开发工具，支持 Microchip PIC 系列芯片。

## 主要工具

| 工具 | 功能 |
|------|------|
| **gpasm** | PIC 汇编器 - 将汇编代码编译为对象文件 |
| **gplink** | PIC 链接器 - 链接对象文件生成可执行文件 |
| **gpdasm** | 反汇编器 - 将二进制文件转换为汇编代码 |
| **gplib** | 库管理工具 - 创建和管理对象文件库 |
| **gpstrip** | 符号剥离工具 - 移除调试符号 |
| **gpvc** | COFF 验证工具 - 检查 COFF 文件格式 |
| **gpvo** | COFF 对象查看工具 - 显示对象文件信息 |

## HarmonyOS 支持

### 已编译版本

- **版本**: 1.5.0
- **状态**: ✅ published
- **平台**: aarch64-unknown-linux-ohos
- **编译日期**: 2026-06-15

### 编译要点

gputils 在 HarmonyOS 平台上的编译主要遇到两个问题：

1. **E007: config.guess 平台识别问题**
   - 原因：旧版本 config.guess 不支持 HarmonyOS
   - 解决：更新 config.guess 和 config.sub 到 automake-1.16 版本

2. **E0XX: umask 077 权限问题**
   - 原因：HMDFS 文件系统下 umask 077 导致临时目录异常
   - 解决：修改 configure 脚本中的 umask 为 022

## 安装方式

### 预编译包安装（推荐）

```bash
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- gputils 1.5.0
```

安装后的工具位于 `~/usr/local/bin/` 目录。

### 手动安装

从归档目录下载预编译包并解压：

```bash
tar -xzf gputils-1.5.0-ohos-aarch64.tar.gz -C ~/usr/local/
```

## 使用示例

### 汇编 PIC 程序

```bash
# 创建汇编文件 example.asm
gpasm example.asm
```

### 铿接对象文件

```bash
gplink -o example.hex example.o
```

### 反汇编二进制

```bash
gpdasm example.hex
```

## 版本历史

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|---------|------|
| 1.5.0 | published | 2026-06-15 | HarmonyOS 平台首次编译 |

## 许可证

GPL-2.0+

## 相关链接

- 官方网站: https://gputils.sourceforge.net/
- 源码下载: https://sourceforge.net/projects/gputils/
- 文档: https://gputils.sourceforge.net/html-help/

## 归档位置

```
archives/g/gputils/
  ├── manifest.yaml      # 软件级元数据
  ├── README.md          # 本文档
  └── 1.5.0/
      ├── manifest.yaml  # 版本级元数据
      ├── notes.md       # 编译笔记
      ├── patches/       # 补丁文件
      ├── packaging/     # 预编译包
      └── reports/       # 测试报告
```

## 质量门禁

| 门禁 | 状态 | 说明 |
|------|------|------|
| G0 - 干净构建 | PASS | 补丁自包含性验证通过 |
| G1 - 二进制完整性 | PASS | 所有工具已编译 |
| G2 - 功能可用性 | PASS | 工具功能验证通过 |
| G3 - 可移植性 | PASS | 无外部依赖 |
| G4 - 档案完整性 | PASS | 归档结构完整 |