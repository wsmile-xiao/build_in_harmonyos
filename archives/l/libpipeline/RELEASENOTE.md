# libpipeline — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf libpipeline-1.5.8-ohos-aarch64.tar.gz -C ~/usr/local

cd libpipeline-1.5.8-ohos-aarch64 && sh install-libpipeline-1.5.8.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.5.8 | success | 9 |

## 当前版本 (1.5.8) 详情

### 包内容
- 二进制: N/A
- 包大小: 2.1MB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 9

### 补丁列表
- 0001-Makefile.patch
- 0002-build-aux-config.guess.patch
- 0003-build-aux-config.sub.patch
- 0004-config.h.patch
- 0005-config.log.patch
- 0006-config.status.patch
- 0007-configure.log.patch
- 0008-gl-lib-Makefile.patch
- 0009-gl-lib-alloca.h.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
