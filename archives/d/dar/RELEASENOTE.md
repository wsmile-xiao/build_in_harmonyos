# dar — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf dar-2.8.1-ohos-aarch64.tar.gz -C ~/usr/local

cd dar-2.8.1-ohos-aarch64 && sh install-dar-2.8.1.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 2.8.1 | partial | 9 |

## 当前版本 (2.8.1) 详情

### 包内容
- 二进制: N/A
- 包大小: 16.0MB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 9

### 补丁列表
- 0001-po-Makefile.in.patch
- 0002-config.guess.patch
- 0003-config.sub.patch
- 0004-po-POTFILES.patch
- 0005-src-check-all_features.patch
- 0006-src-check-bnonzero.patch
- 0007-src-check-padder.patch
- 0008-src-check-uncompressible_file.patch
- 0009-src-dar_suite-dar.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
