# autoconf — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf autoconf-2.72-ohos-aarch64.tar.gz -C ~/usr/local

cd autoconf-2.72-ohos-aarch64 && sh install-autoconf-2.72.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 2.72 | partial | 6 |

## 当前版本 (2.72) 详情

### 包内容
- 二进制: N/A
- 包大小: 3.4MB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 6

### 补丁列表
- 0001-bin-autoconf.patch
- 0002-build-aux-config.guess.patch
- 0003-build-aux-config.sub.patch
- 0004-lib-version.m4.patch
- 0005-tests-atconfig.patch
- 0006-tests-atlocal.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
