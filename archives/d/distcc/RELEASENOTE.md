# distcc — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf distcc-3.4-ohos-aarch64.tar.gz -C ~/usr/local

cd distcc-3.4-ohos-aarch64 && sh install-distcc-3.4.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 3.4 | partial | 5 |

## 当前版本 (3.4) 详情

### 包内容
- 二进制: N/A
- 包大小: 973.2KB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 5

### 补丁列表
- 0001-config.guess.patch
- 0002-config.sub.patch
- 0003-configure.patch
- 0004-src-stats.c.patch
- 0005-src-where.c.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
