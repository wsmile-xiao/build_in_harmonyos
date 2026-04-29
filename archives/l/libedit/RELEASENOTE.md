# libedit — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf libedit-20240817-ohos-aarch64.tar.gz -C ~/usr/local

cd libedit-20240817-ohos-aarch64 && sh install-libedit-20240817.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 20240817 | partial | 9 |

## 当前版本 (20240817) 详情

### 包内容
- 二进制: N/A
- 包大小: 908.2KB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 9

### 补丁列表
- 0001-.patch-ai-review.txt.patch
- 0002-config.guess.patch
- 0003-config.sub.patch
- 0004-doc-editline.3.patch
- 0005-doc-editline.7.patch
- 0006-doc-editrc.5.patch
- 0007-examples-fileman.patch
- 0008-examples-tc1.patch
- 0009-examples-wtc1.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
