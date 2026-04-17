# notcurses — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf notcurses-3.0.17-ohos-aarch64.tar.gz -C ~/usr/local

cd notcurses-3.0.17-ohos-aarch64 && sh install-notcurses-3.0.17.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 3.0.17 | success | 7 |

## 当前版本 (3.0.17) 详情

### 包内容
- 二进制: N/A
- 包大小: 5.8MB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 7

### 补丁列表
- 0001-CMakeLists.txt.patch
- 0002-src-demo-input.c.patch
- 0003-src-demo-reel.c.patch
- 0004-src-lib-fbuf.h.patch
- 0005-src-lib-fd.c.patch
- 0006-src-lib-in.c.patch
- 0007-src-lib-internal.h.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
