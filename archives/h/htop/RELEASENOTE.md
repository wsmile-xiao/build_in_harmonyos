# htop — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf htop-3.4.1-ohos-aarch64.tar.gz -C ~/usr/local

cd htop-3.4.1-ohos-aarch64 && sh install-htop-3.4.1.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 3.4.1 | partial | 3 |

## 当前版本 (3.4.1) 详情

### 包内容
- 二进制: N/A
- 包大小: 672.6KB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 3

### 补丁列表
- 0001-build-aux-config.guess.patch
- 0002-build-aux-config.sub.patch
- 0003-linux-IOPriorityPanel.h.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
