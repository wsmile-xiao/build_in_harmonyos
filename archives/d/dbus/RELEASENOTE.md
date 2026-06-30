# dbus — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf dbus-1.14.10-ohos-aarch64.tar.gz -C ~/usr/local

cd dbus-1.14.10-ohos-aarch64 && sh install-dbus-1.14.10.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.14.10 | partial | 4 |

## 当前版本 (1.14.10) 详情

### 包内容
- 二进制: N/A
- 包大小: 7.1MB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 4

### 补丁列表
- 0001-CMakeLists.txt.patch
- 0002-build-aux-config.guess.patch
- 0003-build-aux-config.sub.patch
- 0004-dbus-CMakeLists.txt.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
