# 3proxy — 轻量多协议代理服务器

## 软件简介

3proxy 是一个轻量级多协议代理服务器，单二进制即可提供 HTTP/HTTPS 代理、
SOCKS4/SOCKS5、SMTP/POP3/FTP 代理、TCP/UDP 端口转发（tcppm/udppm/tlspr）
以及简易 Web 管理界面，支持多种认证方式、访问控制列表（ACL）与日志统计。

**主要组件（安装于 `bin/`）**:
- `3proxy`：一体化主程序（读取一个配置文件即可同时启用多种服务）
- `proxy` / `socks` / `smtpp` / `pop3p` / `ftppr`：各协议的独立守护进程
- `tcppm` / `udppm` / `tlspr`：TCP/UDP/TLS 端口映射
- `mycrypt`：口令哈希工具
- `libexec/3proxy/*.ld.so`：可选插件（Strings / Traffic / PCRE / Transparent）

**配置文件**: `share/3proxy/3proxy.cfg.sample`

## 已编译版本

| 版本 | 状态 | 编译日期 | 补丁数 |
|------|------|----------|--------|
| 0.9.5 | built ✅ | 2026-10-08 | 0 |

## 使用方法

```bash
# 一体化代理：一条配置同时开 HTTP + SOCKS5（非特权端口）
cat > /data/tmp/3proxy.cfg <<CFG
auth none
proxy -p3128
socks -p1080
CFG
3proxy /data/tmp/3proxy.cfg
```

## 构建说明

上游是纯 Makefile 家族（Makefile.Linux/FreeBSD/Solaris/unix/win/msvc/watcom 等
18 个变体），**树内没有 `./configure`**；配方直接 `make -f Makefile.Linux`。
详见各版本目录下的 `notes.md`。

## 参考

- 官网: https://3proxy.org/
- 源码: https://github.com/3proxy/3proxy
- 许可: 3proxy 0.9 Public License（见 `copying`）
