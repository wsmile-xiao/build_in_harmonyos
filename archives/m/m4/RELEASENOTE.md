# m4 — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf m4-1.4.19-ohos-aarch64.tar.gz -C ~/usr/local

cd m4-1.4.19-ohos-aarch64 && sh install-m4-1.4.19.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.4.19 | partial | 6 |

## 当前版本 (1.4.19) 详情

### 包内容
- 二进制: N/A
- 包大小: 391.6KB

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
- 0006-lib-freadahead.c.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
