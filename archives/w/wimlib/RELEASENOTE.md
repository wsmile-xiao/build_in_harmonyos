# wimlib — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf wimlib-1.14.5-ohos-aarch64.tar.gz -C ~/usr/local

cd wimlib-1.14.5-ohos-aarch64 && sh install-wimlib-1.14.5.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.14.5 | partial | 3 |

## 当前版本 (1.14.5) 详情

### 包内容
- 二进制: N/A
- 包大小: 3.9MB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 3

### 补丁列表
- 0001-wimlib-imagex.patch
- 0002-build-aux-config.guess.patch
- 0003-doc-Doxyfile.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
