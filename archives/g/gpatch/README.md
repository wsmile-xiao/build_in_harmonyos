# gpatch (GNU patch)

## 软件简介
GNU patch 是一个用于应用 diff 补丁文件的工具程序。它接受一个包含差异列表的补丁文件，并将这些差异应用到原始文件，从而生成修补后的版本。

## 版本信息
- 当前编译版本: 2.8
- 构建系统: autotools
- 目标平台: ohos-aarch64

## 功能特性
- 支持多种补丁格式（context diff、unified diff、ed scripts）
- 处理多个文件的补丁
- 支持备份原文件
- 提供撤销补丁功能
- 支持合并补丁

## 编译要点
### 必需补丁
编译前需要更新 `build-aux/config.guess` 和 `build-aux/config.sub` 以支持 HarmonyOS 平台识别。

### 配置选项
```bash
./configure --prefix=$DEFAULT_PREFIX
make -j$(nproc)
make install DESTDIR=$TEST_PREFIX
```

### 已知问题
1. **config.status 临时目录权限问题**: HarmonyOS HMDFS 文件系统上 mktemp 创建的临时目录权限异常，需要手动修复 config.status 中的临时目录创建逻辑，使用 `mkdir "$tmp" && chmod 755 "$tmp"`

## 使用验证
```bash
patch --version
# 输出: GNU patch 2.8
```

## 补丁文件清单
- `0001-build-aux-config.guess.patch` - 添加 HarmonyOS 平台识别
- `0002-build-aux-config.sub.patch` - 添加 HarmonyOS 平台识别

## 相关链接
- 官方网站: https://www.gnu.org/software/patch/
- 源码下载: https://ftp.gnu.org/gnu/patch/

---
编译日期: 2026-05-11
编译状态: partial（功能完整，G0验证需手动步骤）