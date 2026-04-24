# p7zip — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf p7zip-17.05-ohos-aarch64.tar.gz -C ~/usr/local

cd p7zip-17.05-ohos-aarch64 && sh install-p7zip-17.05.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 17.05 | partial | 2 |

## 当前版本 (17.05) 详情

### 包内容
- 二进制: N/A
- 包大小: 3.1MB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 2

### 补丁列表
- 0001-CPP-myWindows-config.h.patch
- 0002-makefile.machine.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
