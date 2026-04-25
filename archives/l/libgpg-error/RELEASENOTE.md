# libgpg-error — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf libgpg-error-1.50-ohos-aarch64.tar.gz -C ~/usr/local

cd libgpg-error-1.50-ohos-aarch64 && sh install-libgpg-error-1.50.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 1.55 | partial | 0 |
| 1.50 | partial | 9 |

## 当前版本 (1.50) 详情

### 包内容
- 二进制: N/A
- 包大小: 818.7KB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 9

### 补丁列表
- 0001-po-Makefile.in.patch
- 0002-src-gpg-error-config-test.sh.patch
- 0003-build-aux-config.guess.patch
- 0004-build-aux-config.sub.patch
- 0005-doc-errorref.txt.x.patch
- 0006-doc-gpg-error-config.1.patch
- 0007-doc-gpgrt-config.1.patch
- 0008-lang-cl-gpg-error-codes.lisp.patch
- 0009-po-POTFILES.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
