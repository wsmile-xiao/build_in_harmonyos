# sed — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf sed-4.10-ohos-aarch64.tar.gz -C ~/usr/local

cd sed-4.10-ohos-aarch64 && sh install-sed-4.10.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 4.9 | success | 2 |
| 4.10 | partial | 4 |

## 当前版本 (4.10) 详情

### 包内容
- 二进制: N/A
- 包大小: 576.1KB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 4

### 补丁列表
- 0001-build-aux-config.guess.patch
- 0002-build-aux-config.sub.patch
- 0003-doc-stamp-vti.patch
- 0004-doc-version.texi.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
