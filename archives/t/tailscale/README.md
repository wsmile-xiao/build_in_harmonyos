# Tailscale

Tailscale 是一个零配置 VPN 解决方案，基于 WireGuard 协议构建安全的 mesh 网络。

## 主要组件

- `tailscale`: CLI 命令行工具
- `tailscaled`: 后台守护进程

## 安装

```bash
tar -xzf tailscale-1.90.9-ohos-aarch64.tar.gz -C /
/usr/local/bin/tailscale version
```

## 注意事项

- OpenHarmony 需要 ELF 签名才能执行二进制
- tailscaled 可能需要额外权限配置
