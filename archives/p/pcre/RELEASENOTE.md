# pcre — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf pcre-8.45-ohos-aarch64.tar.gz -C ~/usr/local

cd pcre-8.45-ohos-aarch64 && sh install-pcre-8.45.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 8.45 | partial | 3 |

## 当前版本 (8.45) 详情

### 包内容
- 二进制: N/A
- 包大小: N/A

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 3

### 补丁列表
- 0001-CMakeLists.txt.patch
- 0002-config.guess.patch
- 0003-config.sub.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
