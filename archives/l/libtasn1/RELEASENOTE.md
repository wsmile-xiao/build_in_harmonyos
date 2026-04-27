# libtasn1 — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf libtasn1-4.21.0-ohos-aarch64.tar.gz -C ~/usr/local

cd libtasn1-4.21.0-ohos-aarch64 && sh install-libtasn1-4.21.0.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 4.21.0 | partial | 8 |

## 当前版本 (4.21.0) 详情

### 包内容
- 二进制: N/A
- 包大小: 903.7KB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 8

### 补丁列表
- 0001-.patch-ai-review.txt.patch
- 0002-.pre-scan-report.yaml.patch
- 0003-build-aux-config.guess.patch
- 0004-examples-CertificateExample.patch
- 0005-examples-CrlExample.patch
- 0006-src-asn1Coding.patch
- 0007-src-asn1Decoding.patch
- 0008-src-asn1Parser.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
