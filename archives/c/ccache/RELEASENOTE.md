# ccache — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf ccache-4.12.1-ohos-aarch64.tar.gz -C ~/usr/local

cd ccache-4.12.1-ohos-aarch64 && sh install-ccache-4.12.1.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 4.12.1 | partial | 2 |

## 当前版本 (4.12.1) 详情

### 包内容
- 二进制: N/A
- 包大小: 3.0MB

### 编译信息
- 构建系统: cmake
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 2

### 补丁列表
- 0001-Makefile.patch
- 0002-configure.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
