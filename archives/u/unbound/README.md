# unbound

Unbound 是一个验证型、递归式、缓存 DNS 解析器。由 NLnet Labs 开发，设计目标是快速且精简，支持 DNSSEC 验证。

## 基本信息

- **官网**: https://nlnetlabs.nl/projects/unbound/about/
- **源码**: https://nlnetlabs.nl/downloads/unbound/
- **许可证**: BSD-3-Clause
- **分类**: networking

## 依赖

- OpenSSL (libssl)
- libexpat

## 编译版本

| 版本 | 状态 | 编译日期 | 备注 |
|------|------|----------|------|
| 1.22.0 | built | 2026-05-22 | HarmonyOS aarch64 |

## 使用说明

```bash
# 安装预编译包
curl -fsSL https://gitcode.com/OpenHarmonyPCDeveloper/cmd-pkgs/releases/download/pkgs/install.sh | sh -s -- unbound 1.22.0

# 验证安装
unbound -h
unbound-checkconf -h
```

## 配置示例

```bash
# 启动 DNS 解析器
unbound -c /path/to/unbound.conf

# 检查配置文件
unbound-checkconf /path/to/unbound.conf
```

## 注意事项

- 需要 OpenSSL 和 libexpat 依赖
- HarmonyOS 平台需要应用补丁修复头文件冲突