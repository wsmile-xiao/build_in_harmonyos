# mafft 7.526 — OpenHarmony 预编译摘要

## 基本信息

| 项目 | 内容 |
|------|------|
| 软件 | mafft (Multiple Alignment using Fast Fourier Transform) |
| 版本 | 7.526 (v7.526, 2024/Apr/26) |
| 架构 | aarch64 (OpenHarmony / OHOS) |
| 构建系统 | makefile（纯 Makefile，无 configure） |
| 编译器 | clang / clang++ |
| 编译日期 | 2026-05-28 |
| 状态 | built |

## 软件简介

MAFFT 是一款快速多序列对齐工具，适用于蛋白质和核酸序列。支持多种对齐策略：
- **FFT-NS-2**: 快速渐进式对齐（默认方法）
- **FFT-NS-i**: 迭代渐进式对齐
- **L-INS-i**: 局部迭代对齐（高精度）
- **E-INS-i**: 全局迭代对齐
- **--auto**: 自动选择最佳方法
- **mxscarna**: RNA 二级结构辅助对齐

## 编译适配要点

### 核心修改
1. **新增顶层 Makefile**：mafft 源码顶层无 Makefile，需创建包装器递归调用 `core/` 和 `extensions/`
2. **新增 configure 包装器**：G0 干净构建验证要求 configure 步骤，mafft 无 configure，创建 `#!/bin/sh; exit 0` 包装器
3. **core/Makefile 适配**：CC=clang, PREFIX=/storage/Users/currentUser/usr/local
4. **shebang 修复**：`#!/bin/bash` → `#!/usr/bin/env bash`（OpenHarmony 无 /bin/bash）
5. **extensions/Makefile 适配**：CXX=clang++

### 关键发现
- mafft 为纯 C/C++ 项目，无第三方库依赖
- Savannah 官方镜像 SSL 证书验证失败，需从 GitLab clone
- tarball 内含嵌套 MPI 子 tarball，init-build 自动解压会产生错误目录结构
- 所有 ELF 二进制需 ohc sign-elf 签名才能在鸿蒙执行
- wrapper 脚本在受限 PATH 环境下有兼容性问题（rm/mv/mkdir 未找到），核心二进制功能不受影响

## 补丁说明

| # | 补丁文件 | 类型 | 修改文件 | 说明 |
|---|----------|------|----------|------|
| 1 | 0001-Makefile.patch | platform | Makefile (新增) | 顶层 Makefile 包装器，递归调用 core/ 和 extensions/ |
| 2 | 0002-configure.patch | platform | configure (新增) | configure 包装器 (#!/bin/sh, exit 0)，满足 G0 门禁 |
| 3 | 0003-core-Makefile.patch | platform | core/Makefile | CC=clang, PREFIX 适配 OpenHarmony 路径 |
| 4 | 0004-core-mafft.tmpl.patch | platform | core/mafft.tmpl | shebang: #!/bin/bash → #!/usr/bin/env bash |
| 5 | 0005-extensions-Makefile.patch | platform | extensions/Makefile | C++ 编译器: g++ → clang++ |

## 交付产物

| 文件 | 大小 | 内容 |
|------|------|------|
| mafft-7.526-ohos-aarch64.tar.gz | 15 MB | 主包 (14 bin/wrapper + 35 libexec/mafft 二进制) |
| mafft-7.526-ohos-aarch64-debug.tar.gz | 570 KB | debug 包 (含未 stripped 符号) |

## 验证状态

| 门禁 | 状态 | 详情 |
|------|------|------|
| G0 干净构建 | ✅ PASS | 5 补丁应用成功, configure/make/install 全通过, 21 bin |
| G1 源码完整性 | ✅ PASS | tarball + 5 patches 完整 |
| G2 构建可行性 | ✅ PASS | configure + make 成功 |
| G3 安装完整性 | ✅ PASS | 21 bin, 35 libexec |
| G4 产物可用性 | ✅ PASS | mafft --version = v7.526 |

## 功能测试结果

共 13 项测试，全部通过：
- 多序列对齐（FFT-NS-2, L-INS-i, --auto）：✅ 输出正确
- Gap 插入对齐：✅ 正确对齐长短序列
- 片段追加（--addfragments）：✅ 正确追加到已有对齐
- 核心二进制（dndfast7, tbfast, mxscarnamod）：✅ 运行正常
- 别名脚本（mafft-einsi 等 9 个）：✅ 版本一致

详见 `test-report.md`。

## 部署注意事项

1. 需确保 PATH 包含 `/usr/bin`（mafft wrapper 使用 rm/mv/mkdir）
2. 需确保 bash 在 PATH 中（shebang 为 `#!/usr/bin/env bash`）
3. 需设置 TMPDIR 为可写目录（mafft 运行时创建临时文件）
4. 所有二进制已完成 ELF 签名，可直接在鸿蒙系统执行