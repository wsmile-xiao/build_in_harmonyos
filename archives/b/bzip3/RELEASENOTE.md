# bzip3 — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf bzip3-1.5.3-ohos-aarch64.tar.gz -C ~/usr/local

cd bzip3-1.5.3-ohos-aarch64 && sh install-bzip3-1.5.3.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.5.3 | success | 3 |

## 当前版本 (1.5.3) 详情

### 包内容
- 二进制: N/A
- 包大小: 268.1KB

### 编译信息
- 构建系统: cmake
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 3

### 补丁列表
- 0001-build-aux-config.guess.patch
- 0002-bzip3-config.cmake.in.patch
- 0003-configure.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
