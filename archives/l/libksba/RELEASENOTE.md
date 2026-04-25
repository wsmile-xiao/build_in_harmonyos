# libksba — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf libksba-1.6.7-ohos-aarch64.tar.gz -C ~/usr/local

cd libksba-1.6.7-ohos-aarch64 && sh install-libksba-1.6.7.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.6.7 | partial | 6 |

## 当前版本 (1.6.7) 详情

### 包内容
- 二进制: N/A
- 包大小: 409.1KB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 6

### 补丁列表
- 0001-build-aux-config.guess.patch
- 0002-build-aux-config.sub.patch
- 0003-gl-alloca.h.patch
- 0004-src-ksba-config.patch
- 0005-src-versioninfo.rc.patch
- 0006-tests-oidtranstbl.h.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
