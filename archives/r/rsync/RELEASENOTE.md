# rsync — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf rsync-3.3.0-ohos-aarch64.tar.gz -C ~/usr/local

cd rsync-3.3.0-ohos-aarch64 && sh install-rsync-3.3.0.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 3.3.0 | partial | 2 |

## 当前版本 (3.3.0) 详情

### 包内容
- 二进制: N/A
- 包大小: 2.8MB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 2

### 补丁列表
- 0001-config-guess-harmonyos.patch
- 0002-config-sub-harmonyos.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
