# openssl — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf openssl-1.1.1w-ohos-aarch64.tar.gz -C ~/usr/local

cd openssl-1.1.1w-ohos-aarch64 && sh install-openssl-1.1.1w.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.1.1w | success | 2 |

## 当前版本 (1.1.1w) 详情

### 包内容
- 二进制: N/A
- 包大小: 15.5MB

### 编译信息
- 构建系统: custom-perl
- 目标: ohos-aarch64
- 质量门禁: FAIL-WARN
- 补丁数: 2

### 补丁列表
- 0001-Configurations-openharmony-conf.patch
- 0002-Configure.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
