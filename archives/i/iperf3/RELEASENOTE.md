# iperf3 — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf iperf3-3.18-ohos-aarch64.tar.gz -C ~/usr/local

cd iperf3-3.18-ohos-aarch64 && sh install-iperf3-3.18.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 3.18 | partial | 6 |

## 当前版本 (3.18) 详情

### 包内容
- 二进制: N/A
- 包大小: 234.6KB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 6

### 补丁列表
- 0001-CMakeLists.txt.patch
- 0002-src-pthread_stubs.c.patch
- 0003-config-config.guess.patch
- 0004-config-config.sub.patch
- 0005-src-iperf_config.h.patch
- 0006-src-version.h.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
