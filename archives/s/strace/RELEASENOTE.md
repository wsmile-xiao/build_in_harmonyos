# strace — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf strace-6.19-ohos-aarch64.tar.gz -C ~/usr/local

cd strace-6.19-ohos-aarch64 && sh install-strace-6.19.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 6.19 | partial | 5 |

## 当前版本 (6.19) 详情

### 包内容
- 二进制: N/A
- 包大小: 2.1MB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 5

### 补丁列表
- 0001-build-aux-config.guess.patch
- 0002-build-aux-config.sub.patch
- 0003-debian-changelog.patch
- 0004-src-sigreturn.c.patch
- 0005-strace.spec.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
