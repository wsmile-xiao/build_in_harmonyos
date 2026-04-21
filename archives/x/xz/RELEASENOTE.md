# xz — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf xz-5.6.2-ohos-aarch64.tar.gz -C ~/usr/local

cd xz-5.6.2-ohos-aarch64 && sh install-xz-5.6.2.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 5.6.2 | partial | 9 |

## 当前版本 (5.6.2) 详情

### 包内容
- 二进制: N/A
- 包大小: 3.1MB

### 编译信息
- 构建系统: unknown
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 9

### 补丁列表
- 0001-po-Makefile.in.patch
- 0002-build-aux-config.guess.patch
- 0003-build-aux-config.sub.patch
- 0004-po-POTFILES.patch
- 0005-src-lzmainfo-lzmainfo.patch
- 0006-src-scripts-xzdiff.patch
- 0007-src-scripts-xzgrep.patch
- 0008-src-scripts-xzless.patch
- 0009-src-scripts-xzmore.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
