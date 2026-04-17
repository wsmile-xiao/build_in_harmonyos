# python — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf python-3.12.9-ohos-aarch64.tar.gz -C ~/usr/local

cd python-3.12.9-ohos-aarch64 && sh install-python-3.12.9.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 3.9.25 | tested | 9 |
| 3.9.0 | partial | 9 |
| 3.12.9 | partial  # 416 OK / 11 failed, 共享库启用, 纯净包 38MB | 6 |

## 当前版本 (3.12.9) 详情

### 包内容
- 二进制: N/A
- 包大小: 153.5MB

### 编译信息
- 构建系统: autotools (PY_STDLIB_MOD 宏系统)
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 6

### 补丁列表
- 0001-config.guess-HarmonyOS-support.patch
- 0002-config.sub-HarmonyOS-support.patch
- 0003-configure.ac-HarmonyOS-support.patch
- 0004-Makefile.pre.in-HarmonyOS-ln-fix.patch
- 0005-Modules-Setup.stdlib.in-HarmonyOS-sysroot.patch
- 0009-Modules-timemodule.c-OHOS-musl-timezone.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
