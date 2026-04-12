# readline — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf readline-8.2-ohos-aarch64.tar.gz -C ~/usr/local

cd readline-8.2-ohos-aarch64 && sh install-readline-8.2.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 8.2 | success | 2 |

## 当前版本 (8.2) 详情

### 包内容
- 二进制: N/A
- 包大小: 3.3MB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 2

### 补丁列表
- 0001-port-for-ohos.patch
- 0002-fix-shlib-termcap-link.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
