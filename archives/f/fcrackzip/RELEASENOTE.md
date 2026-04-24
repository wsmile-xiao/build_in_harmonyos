# fcrackzip — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf fcrackzip-1.0-ohos-aarch64.tar.gz -C ~/usr/local

cd fcrackzip-1.0-ohos-aarch64 && sh install-fcrackzip-1.0.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.0 | partial | 3 |

## 当前版本 (1.0) 详情

### 包内容
- 二进制: N/A
- 包大小: 233.1KB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 3

### 补丁列表
- 0001-crack.h.patch
- 0002-getopt.c.patch
- 0003-getopt1.c.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
