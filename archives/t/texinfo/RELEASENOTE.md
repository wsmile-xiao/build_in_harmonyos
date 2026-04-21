# texinfo — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf texinfo-7.3-ohos-aarch64.tar.gz -C ~/usr/local

cd texinfo-7.3-ohos-aarch64 && sh install-texinfo-7.3.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 7.3 | success | 9 |

## 当前版本 (7.3) 详情

### 包内容
- 二进制: N/A
- 包大小: 1.1MB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 9

### 补丁列表
- 0001-Makefile.patch
- 0002-Pod-Simple-Texinfo-Makefile.patch
- 0003-Pod-Simple-Texinfo-pod2texi.patch
- 0004-build-aux-config.guess.patch
- 0005-build-aux-config.sub.patch
- 0006-tta-build-aux-config.guess.patch
- 0007-tta-build-aux-config.sub.patch
- 0008-tta-perl-CheckXS-build-aux-config.guess.patch
- 0009-tta-perl-CheckXS-build-aux-config.sub.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
