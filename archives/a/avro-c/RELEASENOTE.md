# avro-c — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf avro-c-1.12.0-ohos-aarch64.tar.gz -C ~/usr/local

cd avro-c-1.12.0-ohos-aarch64 && sh install-avro-c-1.12.0.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.12.0 | partial | 3 |

## 当前版本 (1.12.0) 详情

### 包内容
- 二进制: N/A
- 包大小: 2.3MB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 3

### 补丁列表
- 0001-CMakeLists.txt.patch
- 0002-src-CMakeLists.txt.patch
- 0003-version.sh.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
