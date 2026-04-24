# libsodium — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf libsodium-1.0.22-ohos-aarch64.tar.gz -C ~/usr/local

cd libsodium-1.0.22-ohos-aarch64 && sh install-libsodium-1.0.22.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.0.22 | partial | 2 |

## 当前版本 (1.0.22) 详情

### 包内容
- 二进制: N/A
- 包大小: 1.6MB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 2

### 补丁列表
- 0001-build-aux-config.guess.patch
- 0002-build-aux-config.sub.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
