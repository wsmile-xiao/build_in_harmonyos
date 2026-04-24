# ttaenc — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf ttaenc-3.4.1-ohos-aarch64.tar.gz -C ~/usr/local

cd ttaenc-3.4.1-ohos-aarch64 && sh install-ttaenc-3.4.1.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 3.4.1 | partial | 4 |

## 当前版本 (3.4.1) 详情

### 包内容
- 二进制: N/A
- 包大小: 95.1KB

### 编译信息
- 构建系统: makefile
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 4

### 补丁列表
- 0001-Makefile.patch
- 0002-configure.patch
- 0003-ttaenc.c.patch
- 0004-ttaenc.h.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
