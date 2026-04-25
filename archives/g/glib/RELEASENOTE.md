# glib — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf glib-2.88.0-ohos-aarch64.tar.gz -C ~/usr/local

cd glib-2.88.0-ohos-aarch64 && sh install-glib-2.88.0.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 2.88.0 | partial | 4 |

## 当前版本 (2.88.0) 详情

### 包内容
- 二进制: N/A
- 包大小: 143.9MB

### 编译信息
- 构建系统: meson
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 4

### 补丁列表
- 0001-gio-gnetworkmonitornetlink.c.patch
- 0002-gio-meson.build.patch
- 0003-glib-meson.build.patch
- 0004-meson.build.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
