# zsh — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf zsh-5.9-ohos-aarch64.tar.gz -C ~/usr/local

cd zsh-5.9-ohos-aarch64 && sh install-zsh-5.9.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 5.9 | partial | 9 |

## 当前版本 (5.9) 详情

### 包内容
- 二进制: N/A
- 包大小: 14.0MB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 9

### 补丁列表
- 0001-.patch-ai-review.txt.patch
- 0002-config.modules.sh.patch
- 0003-Config-defs.mk.patch
- 0004-Src-Makemod.in.patch
- 0005-Src-signames.c.patch
- 0006-Src-Builtins-Makefile.in.patch
- 0007-Src-Modules-Makefile.in.patch
- 0008-Src-Modules-errnames.c.patch
- 0009-Src-Zle-Makefile.in.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
