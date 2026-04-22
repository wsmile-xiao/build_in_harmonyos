# speex — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf speex-1.2.1-ohos-aarch64.tar.gz -C ~/usr/local

cd speex-1.2.1-ohos-aarch64 && sh install-speex-1.2.1.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.2.1 | partial | 5 |

## 当前版本 (1.2.1) 详情

### 包内容
- 二进制: N/A
- 包大小: 420.6KB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 5

### 补丁列表
- 0001-Makefile.manual.patch
- 0002-config.guess.patch
- 0003-config.h.patch
- 0004-config.sub.patch
- 0005-include-speex-speex_config_types.h.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
