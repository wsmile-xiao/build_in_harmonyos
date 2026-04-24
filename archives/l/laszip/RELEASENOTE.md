# laszip — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf laszip-3.5.0-ohos-aarch64.tar.gz -C ~/usr/local

cd laszip-3.5.0-ohos-aarch64 && sh install-laszip-3.5.0.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 3.5.0 | partial | 2 |

## 当前版本 (3.5.0) 详情

### 包内容
- 二进制: N/A
- 包大小: 1.2MB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 2

### 补丁列表
- 0001-CMakeLists.txt.patch
- 0002-src-mydefs.cpp.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
