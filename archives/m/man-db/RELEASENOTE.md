# man-db — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf man-db-2.13.1-ohos-aarch64.tar.gz -C ~/usr/local

cd man-db-2.13.1-ohos-aarch64 && sh install-man-db-2.13.1.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 2.13.1 | success | 5 |

## 当前版本 (2.13.1) 详情

### 包内容
- 二进制: N/A
- 包大小: 2.9MB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 5

### 补丁列表
- 0001-build-aux-config.guess.patch
- 0002-build-aux-config.sub.patch
- 0003-lib-encodings.c.patch
- 0004-lib-security.c.patch
- 0005-src-man.c.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
