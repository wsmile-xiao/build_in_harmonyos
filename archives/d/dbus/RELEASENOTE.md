# dbus — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf dbus-1.14.10.2-ohos-aarch64.tar.gz -C ~/usr/local

cd dbus-1.14.10.2-ohos-aarch64 && sh install-dbus-1.14.10.1.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.14.10.2 | published | 4 |

## 当前版本 (1.14.10.2) 详情

### 包内容
- 二进制: dbus-daemon / dbus-run-session / dbus-send / dbus-monitor / dbus-uuidgen / dbus-cleanup-sockets / dbus-launch / dbus-test-tool / dbus-update-activation-environment（共 9 个 CLI 工具）
- 库: libdbus-1.a（静态客户端库）
- 配置: share/dbus-1/session.conf

### 编译信息
- 构建系统: cmake
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