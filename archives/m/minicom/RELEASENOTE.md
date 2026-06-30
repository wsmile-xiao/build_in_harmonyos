# minicom — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf minicom-2.10-ohos-aarch64.tar.gz -C ~/usr/local

cd minicom-2.10-ohos-aarch64 && sh install-minicom-2.10.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 2.10 | success | 9 |

## 当前版本 (2.10) 详情

### 包内容
- 二进制: N/A
- 包大小: 1.2MB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 9

### 补丁列表
- 0001-.patch-ai-review.txt.patch
- 0002-main.c.patch
- 0003-po-Makefile.in.patch
- 0004-src-keyserv.c.patch
- 0005-src-main.c.patch
- 0006-src-minicom.c.patch
- 0007-src-script.c.patch
- 0008-minicom.spec.patch
- 0009-missing-aclocal.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
