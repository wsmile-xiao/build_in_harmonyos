# bcrypt — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf bcrypt-1.0-ohos-aarch64.tar.gz -C ~/usr/local

cd bcrypt-1.0-ohos-aarch64 && sh install-bcrypt-1.0.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.0 | success | 2 |

## 当前版本 (1.0) 详情

### 包内容
- 二进制: N/A
- 包大小: 33.5KB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 2

### 补丁列表
- 0001-Makefile.patch
- 0002-crypt_blowfish-Makefile.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
