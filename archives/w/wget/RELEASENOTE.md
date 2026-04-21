# wget — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf wget-1.19.1-ohos-aarch64.tar.gz -C ~/usr/local

cd wget-1.19.1-ohos-aarch64 && sh install-wget-1.19.1.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.19.1 | success | 6 |

## 当前版本 (1.19.1) 详情

### 包内容
- 二进制: N/A
- 包大小: 10.9MB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 6

### 补丁列表
- 0001-build-aux-config.guess.patch
- 0002-build-aux-config.sub.patch
- 0003-configure.patch
- 0004-doc-stamp-vti.patch
- 0005-doc-version.texi.patch
- 0006-lib-tmpdir.c.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
