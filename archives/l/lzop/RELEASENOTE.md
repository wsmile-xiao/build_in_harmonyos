# lzop — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf lzop-1.04-ohos-aarch64.tar.gz -C ~/usr/local

cd lzop-1.04-ohos-aarch64 && sh install-lzop-1.04.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.04 | partial | 9 |

## 当前版本 (1.04) 详情

### 包内容
- 二进制: N/A
- 包大小: 365.1KB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 9

### 补丁列表
- 0001-CMakeLists.txt.patch
- 0002-Makefile.in.patch
- 0003-aclocal.m4.patch
- 0004-autoconf-config.guess~.patch
- 0005-autoconf-config.sub~.patch
- 0006-autoconf-install-sh~.patch
- 0007-autoconf-compile.patch
- 0008-autoconf-config.guess.patch
- 0009-autoconf-config.sub.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
