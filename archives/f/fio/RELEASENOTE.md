# fio — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf fio-3.41-ohos-aarch64.tar.gz -C ~/usr/local

cd fio-3.41-ohos-aarch64 && sh install-fio-3.41.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 3.41 | partial | 1 |

## 当前版本 (3.41) 详情

### 包内容
- 二进制: N/A
- 包大小: 1.7MB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 1

### 补丁列表
- 0001-oslib-linux-blkzoned.c.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
