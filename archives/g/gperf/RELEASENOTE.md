# gperf — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf gperf-3.1-ohos-aarch64.tar.gz -C ~/usr/local

cd gperf-3.1-ohos-aarch64 && sh install-gperf-3.1.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 3.1 | success | 5 |

## 当前版本 (3.1) 详情

### 包内容
- 二进制: gperf (GNU gperf 3.1)
- 包大小: 372KB (主包) + 48KB (debug包)

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 5

### 补丁列表
- 0001-configure.patch
- 0002-doc-configure.patch
- 0003-lib-configure.patch
- 0004-src-configure.patch
- 0005-tests-configure.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
