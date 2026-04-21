# tar — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf tar-1.35-ohos-aarch64.tar.gz -C ~/usr/local

cd tar-1.35-ohos-aarch64 && sh install-tar-1.35.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.35 | partial | 9 |

## 当前版本 (1.35) 详情

### 包内容
- 二进制: N/A
- 包大小: 3.8MB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 9

### 补丁列表
- 0001-Makefile.patch
- 0002-config.log.patch
- 0003-config.status.patch
- 0004-configure.patch
- 0005-doc-Makefile.patch
- 0006-doc-stamp-vti.patch
- 0007-doc-tar.info.patch
- 0008-doc-tar.info-1.patch
- 0009-doc-tar.info-2.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
