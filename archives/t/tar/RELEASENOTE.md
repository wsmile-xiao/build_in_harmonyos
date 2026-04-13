# tar — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf tar-1.35-ohos-aarch64.tar.gz -C ~/usr/local

cd tar-1.35-ohos-aarch64 && sh install-tar-1.35.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.35 | partial | 7 |

## 当前版本 (1.35) 详情

### 包内容
- 二进制: N/A
- 包大小: 1.4MB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 7

### 补丁列表
- 0001-build-aux-config.guess.patch
- 0002-build-aux-config.sub.patch
- 0003-lib-rmt-command.h.patch
- 0004-po-Makefile.in.patch
- 0005-po-POTFILES.patch
- 0006-tests-atconfig.patch
- 0007-tests-atlocal.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
