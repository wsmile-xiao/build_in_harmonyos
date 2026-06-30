# libsmi — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf libsmi-0.5.0-ohos-aarch64.tar.gz -C ~/usr/local

cd libsmi-0.5.0-ohos-aarch64 && sh install-libsmi-0.5.0.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 0.5.0 | partial | 9 |

## 当前版本 (0.5.0) 详情

### 包内容
- 二进制: N/A
- 包大小: N/A

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 9

### 补丁列表
- 0001-config.guess.patch
- 0002-configure.patch
- 0003-lib-smi_config.3.patch
- 0004-libsmi.pc.patch
- 0005-test-parser.test.patch
- 0006-test-smidiff.test.patch
- 0007-test-smidump-cm.test.patch
- 0008-test-smidump-corba.test.patch
- 0009-test-smidump-identifiers.test.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
