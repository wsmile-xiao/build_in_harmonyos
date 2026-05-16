# libccd — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf libccd-2.1-ohos-aarch64.tar.gz -C ~/usr/local

cd libccd-2.1-ohos-aarch64 && sh install-libccd-2.1.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 2.1 | success | 3 |

## 当前版本 (2.1) 详情

### 包内容
- 二进制: N/A
- 包大小: 150.1KB

### 编译信息
- 构建系统: cmake
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 3

### 补丁列表
- 0001-CMakeLists.txt.patch
- 0002-src-CMakeLists.txt.patch
- 0003-src-testsuites-cu-CMakeLists.txt.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
