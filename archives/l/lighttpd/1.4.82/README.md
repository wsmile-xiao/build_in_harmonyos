# Lighttpd 1.4.82 for OpenHarmony

## 简介

Lighttpd 是一款轻量级、高性能的开源 Web 服务器，专为速度关键型环境设计。它具有低内存占用、低 CPU 负载、高速度的特点，非常适合高负载环境。

**版本**: 1.4.82  
**平台**: OpenHarmony (aarch64)  
**构建日期**: 2026-05-23

## 特性

- ✅ 低内存占用和高性能
- ✅ FastCGI、SCGI、CGI 支持
- ✅ HTTP/2 支持 (mod_h2)
- ✅ TLS/SSL 支持 (mod_openssl)
- ✅ 压缩支持 (mod_deflate)
- ✅ 反向代理支持 (mod_proxy)
- ✅ WebDAV 支持 (mod_webdav)
- ✅ WebSocket 支持 (mod_wstunnel)

## 依赖项

本编译版本依赖以下库：

- **openssl**: TLS/SSL 加密支持
- **zlib**: 压缩功能支持
- **pcre2**: 正则表达式支持

## 目录结构

```
lighttpd-1.4.82/
├── bin/
│   └── lighttpd              # 主程序
├── lib/
│   ├── mod_accesslog.so      # 访问日志模块
│   ├── mod_ajp13.so          # AJP13 协议模块
│   ├── mod_auth.so           # 认证模块
│   ├── mod_authn_file.so     # 文件认证模块
│   ├── mod_cgi.so            # CGI 模块
│   ├── mod_deflate.so        # 压缩模块
│   ├── mod_dirlisting.so     # 目录列表模块
│   ├── mod_extforward.so     # 外部转发模块
│   ├── mod_h2.so             # HTTP/2 模块
│   ├── mod_openssl.so        # OpenSSL 模块
│   ├── mod_proxy.so          # 代理模块
│   ├── mod_rrdtool.so        # RRDtool 模块
│   ├── mod_sockproxy.so      # Socket 代理模块
│   ├── mod_ssi.so            # SSI 模块
│   ├── mod_status.so         # 状态监控模块
│   ├── mod_userdir.so        # 用户目录模块
│   ├── mod_vhostdb.so        # 虚拟主机数据库模块
│   ├── mod_webdav.so         # WebDAV 模块
│   └── mod_wstunnel.so       # WebSocket 隧道模块
├── reports/
│   ├── build.log             # 编译日志
│   ├── configure.log         # 配置日志
│   └── install.log           # 安装日志
├── patches/                  # 补丁目录（如有）
├── packaging/                # 预编译包目录
├── manifest.yaml             # 元数据清单
└── README.md                 # 本文档
```

## 模块加载方法

Lighttpd 通过配置文件加载模块。在 `lighttpd.conf` 中使用 `server.modules` 指令：

```conf
server.modules = (
    "mod_accesslog",
    "mod_openssl",
    "mod_deflate",
    "mod_proxy",
    "mod_h2"
)
```

### 常用模块说明

| 模块 | 用途 | 说明 |
|------|------|------|
| mod_accesslog | 访问日志 | 记录 HTTP 请求日志 |
| mod_auth | 认证 | HTTP 基本认证和摘要认证 |
| mod_cgi | CGI | 执行 CGI 程序 |
| mod_deflate | 压缩 | 响应内容压缩（gzip/deflate） |
| mod_h2 | HTTP/2 | HTTP/2 协议支持 |
| mod_openssl | TLS/SSL | HTTPS 支持 |
| mod_proxy | 代理 | 反向代理支持 |
| mod_webdav | WebDAV | WebDAV 协议支持 |
| mod_wstunnel | WebSocket | WebSocket 隧道支持 |

## OpenHarmony 配置注意事项

### 1. 库路径配置

确保系统能找到依赖库：

```bash
export LD_LIBRARY_PATH=/system/lib64:$LD_LIBRARY_PATH
```

### 2. 配置文件路径

创建配置文件目录：

```bash
mkdir -p /etc/lighttpd
mkdir -p /var/log/lighttpd
mkdir -p /var/run/lighttpd
```

### 3. 模块路径

在配置文件中指定模块路径：

```conf
server.modules-dir = "/path/to/lighttpd/lib"
```

### 4. 用户权限

建议使用非特权用户运行：

```bash
# 创建 lighttpd 用户
useradd -r -s /sbin/nologin lighttpd

# 在配置文件中设置
server.username = "lighttpd"
server.groupname = "lighttpd"
```

### 5. HTTP/2 配置

启用 HTTP/2 支持：

```conf
server.modules += ( "mod_h2" )
$HTTP["scheme"] == "https" {
    h2.server-push = "enable"
}
```

### 6. TLS/SSL 配置

配置 HTTPS：

```conf
server.modules += ( "mod_openssl" )
$SERVER["socket"] == ":443" {
    ssl.engine = "enable"
    ssl.pemfile = "/path/to/cert.pem"
    ssl.privkey = "/path/to/key.pem"
}
```

### 7. 性能优化

针对 OpenHarmony 设备的优化建议：

```conf
# 工作进程数（建议为 CPU 核心数）
server.max-worker = 4

# 最大并发连接
server.max-connections = 1024

# 最大文件描述符
server.max-fd = 2048

# 启用压缩
server.modules += ( "mod_deflate" )
deflate.mimetypes = ( "text/html", "text/plain", "text/css", "application/javascript" )
```

## 快速启动

```bash
# 启动服务器
./bin/lighttpd -f /etc/lighttpd/lighttpd.conf

# 测试配置文件
./bin/lighttpd -t -f /etc/lighttpd/lighttpd.conf

# 前台运行（调试模式）
./bin/lighttpd -D -f /etc/lighttpd/lighttpd.conf
```

## 故障排查

### 模块加载失败

检查库依赖：

```bash
ldd lib/mod_*.so | grep "not found"
```

### 权限问题

确保日志和运行目录权限正确：

```bash
chown -R lighttpd:lighttpd /var/log/lighttpd
chown -R lighttpd:lighttpd /var/run/lighttpd
```

### TLS 证书问题

确保证书格式正确：

```bash
openssl x509 -in cert.pem -text -noout
```

## 预编译包

预编译包 `lighttpd-1.4.82-ohos-aarch64.tar.gz` 包含：
- bin/ 目录：主程序
- lib/ 目录：所有模块

安装方法：

```bash
tar xzf lighttpd-1.4.82-ohos-aarch64.tar.gz -C /usr/local/
```

## 相关资源

- 官方网站: https://www.lighttpd.net/
- 文档: https://redmine.lighttpd.net/projects/lighttpd/wiki
- 配置示例: https://redmine.lighttpd.net/projects/lighttpd/wiki/TutorialConfiguration

## 许可证

Lighttpd 采用 BSD-3-Clause 许可证。详见 COPYING 文件。

---

**构建信息**
- 构建时间: 2026-05-23
- 构建平台: OpenHarmony
- 目标架构: aarch64
- 编译器: clang