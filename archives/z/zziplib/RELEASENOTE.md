# zziplib — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf zziplib-0.13.78-ohos-aarch64.tar.gz -C ~/usr/local

cd zziplib-0.13.78-ohos-aarch64 && sh install-zziplib-0.13.78.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 0.13.78 | partial | 9 |

## 当前版本 (0.13.78) 详情

### 包内容
- 二进制: N/A
- 包大小: N/A

### 编译信息
- 构建系统: cmake
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 9

### 补丁列表
- 0001-CMakeLists.txt.patch
- 0002-SDL-CMakeLists.txt.patch
- 0003-bins-CMakeLists.txt.patch
- 0004-config.guess.patch
- 0005-config.sub.patch
- 0006-docs-CMakeLists.txt.patch
- 0007-test-CMakeLists.txt.patch
- 0008-uses-config.guess.patch
- 0009-uses-config.sub.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
