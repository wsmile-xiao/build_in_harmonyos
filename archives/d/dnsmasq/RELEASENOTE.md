# dnsmasq — HarmonyOS aarch64 预编译包

## 快速安装

```bash
tar xzf dnsmasq-2.92-ohos-aarch64.tar.gz -C ~/usr/local

cd dnsmasq-2.92-ohos-aarch64 && sh install-dnsmasq-2.92.sh
```

## 可用版本

| 版本 | 状态 | 补丁数 |
|------|------|--------|
| 2.92 | success | 2 |

## 当前版本 (2.92) 详情

### 包内容
- 二进制: N/A
- 包大小: 577.6KB

### 编译信息
- 构建系统: autotools
- 目标: ohos-aarch64
- 质量门禁: PASS
- 补丁数: 2

### 补丁列表
- 0001-src-ipset.c.patch
- 0002-src-netlink.c.patch

## 环境要求
- HarmonyOS/OpenHarmony aarch64
- `openharmony-compile-agent/usr/local/bin` in PATH
