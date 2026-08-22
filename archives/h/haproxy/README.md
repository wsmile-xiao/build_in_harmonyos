# HAProxy 3.2.0 for OpenHarmony

## 软件简介

HAProxy 是一个免费、开源、高性能的 TCP/HTTP 负载均衡器和代理服务器，特别适用于高可用性环境。它可以将请求分发到多个服务器，提高网站和应用程序的性能和可靠性。

### 主要特性

- **高性能负载均衡**：支持 TCP 和 HTTP 模式，处理数万并发连接
- **SSL/TLS 支持**：内置 SSL 终止和加密功能
- **健康检查**：自动检测后端服务器健康状态
- **会话保持**：支持基于 Cookie 和 IP 的会话粘性
- **监控统计**：提供详细的实时统计页面
- **灵活配置**：支持复杂的路由规则和 ACL
- **HTTP/2 支持**：原生支持 HTTP/2 协议
- **压缩支持**：支持 gzip 压缩以减少带宽使用

## 版本信息

- **版本**: 3.2.0
- **构建平台**: OpenHarmony
- **架构**: aarch64 (ARM64)
- **构建日期**: 2026-05-23

## 依赖要求

HAProxy 运行时需要以下库：

1. **OpenSSL** (>= 1.1.1)
   - 用于 SSL/TLS 加密
   - 版本要求：1.1.1 或更高

2. **zlib** (>= 1.2.11)
   - 用于压缩支持
   - 版本要求：1.2.11 或更高

3. **PCRE2** (>= 10.0)
   - 用于正则表达式匹配
   - 版本要求：10.0 或更高

## 安装方法

### 方法 1: 使用预编译包

```bash
# 解压预编译包
tar xzf haproxy-3.2.0-ohos-aarch64.tar.gz

# 复制到系统目录
cp bin/haproxy /usr/local/bin/
chmod +x /usr/local/bin/haproxy
```

### 方法 2: 直接使用二进制文件

```bash
# 直接运行
./bin/haproxy -v

# 查看帮助
./bin/haproxy -h
```

## 配置方法

### 基本配置示例

创建配置文件 `/etc/haproxy/haproxy.cfg`:

```haproxy
global
    log /dev/log local0
    log /dev/log local1 notice
    chroot /var/lib/haproxy
    stats socket /run/haproxy/admin.sock mode 660 level admin
    stats timeout 30s
    user haproxy
    group haproxy
    daemon

defaults
    log     global
    mode    http
    option  httplog
    option  dontlognull
    timeout connect 5000
    timeout client  50000
    timeout server  50000

frontend http_front
    bind *:80
    stats uri /haproxy?stats
    default_backend http_back

backend http_back
    balance roundrobin
    server backend1 192.168.1.100:80 check
    server backend2 192.168.1.101:80 check
```

### 启动 HAProxy

```bash
# 测试配置文件
haproxy -c -f /etc/haproxy/haproxy.cfg

# 启动服务
haproxy -f /etc/haproxy/haproxy.cfg

# 后台运行
haproxy -D -f /etc/haproxy/haproxy.cfg
```

### SSL/TLS 配置示例

```haproxy
frontend https_front
    bind *:443 ssl crt /etc/haproxy/certs/server.pem
    redirect scheme https if !{ ssl_fc }
    default_backend http_back
```

## OpenHarmony 注意事项

### 1. 动态链接库

此版本为动态链接可执行文件，依赖以下库：

```bash
# 检查依赖
ldd bin/haproxy
```

确保系统已安装所需依赖库：
- libssl.so (OpenSSL)
- libcrypto.so (OpenSSL)
- libz.so (zlib)
- libpcre2.so (PCRE2)

### 2. 系统资源限制

OpenHarmony 可能对进程资源有限制，建议调整：

```bash
# 增加文件描述符限制
ulimit -n 65535

# 增加进程数限制
ulimit -u 4096
```

### 3. 网络配置

确保网络配置允许 HAProxy 绑定所需端口：

```bash
# 检查端口占用
netstat -tulpn | grep :80
netstat -tulpn | grep :443
```

### 4. 日志系统

OpenHarmony 使用不同的日志系统，配置 HAProxy 日志：

```haproxy
global
    log stdout format raw local0 info
    # 或使用 syslog
    log /dev/log local0
```

### 5. 性能优化建议

针对 OpenHarmony ARM64 平台的优化建议：

- **CPU 亲和性**: 根据系统 CPU 核心数调整 nbproc 和 nbthread
- **内存限制**: 监控内存使用，调整 maxconn 参数
- **连接超时**: 根据网络环境调整超时参数
- **缓冲区大小**: 根据应用需求调整 tune.bufsize

```haproxy
global
    # 多进程模式（根据 CPU 核心数调整）
    nbproc 2
    # 每进程线程数
    nbthread 4
    
defaults
    # 最大连接数
    maxconn 10000
    # 缓冲区大小
    tune.bufsize 32768
```

### 6. 服务管理

在 OpenHarmony 上管理 HAProxy 服务：

```bash
# 创建 systemd 服务文件（如果支持）
cat > /etc/systemd/system/haproxy.service <<EOF
[Unit]
Description=HAProxy Load Balancer
After=network.target

[Service]
Type=forking
ExecStart=/usr/local/bin/haproxy -f /etc/haproxy/haproxy.cfg
ExecReload=/usr/local/bin/haproxy -f /etc/haproxy/haproxy.cfg -p /run/haproxy.pid -sf $(cat /run/haproxy.pid)
PIDFile=/run/haproxy.pid
Restart=on-failure

[Install]
WantedBy=multi-user.target
EOF

# 启用并启动服务
systemctl enable haproxy
systemctl start haproxy
```

## 验证安装

```bash
# 检查版本
haproxy -v

# 输出示例：
# HAProxy 3.2.0
# Build options: TARGET=linux-musl CPU=generic CC=gcc CFLAGS="-O2 -g -fno-strict-aliasing" FEATURES="getaddrinfo"
```

## 监控和统计

访问统计页面：
```
http://your-server-ip/haproxy?stats
```

或使用命令行工具：
```bash
# 通过 Unix socket 查看统计信息
echo "show stat" | socat stdio /run/haproxy/admin.sock
```

## 故障排查

### 常见问题

1. **无法启动**: 检查配置文件语法 `haproxy -c -f /path/to/config`
2. **依赖缺失**: 使用 `ldd haproxy` 检查动态库依赖
3. **权限问题**: 确保 HAProxy 用户有足够权限
4. **端口被占用**: 检查并释放被占用的端口

### 日志位置

```bash
# 查看系统日志
journalctl -u haproxy

# 或查看 haproxy 日志文件
tail -f /var/log/haproxy.log
```

## 参考资源

- [HAProxy 官方文档](https://www.haproxy.org/documentation.html)
- [HAProxy 配置手册](https://cbonte.github.io/haproxy-dconv/)
- [OpenHarmony 开发者文档](https://www.openharmony.cn/)

## 文件结构

```
archives/h/haproxy/3.2.0/
├── bin/                           # 可执行文件
│   └── haproxy                    # HAProxy 主程序 (14MB)
├── lib/                           # 库文件（无）
├── include/                       # 头文件（无）
├── patches/                       # 补丁文件
├── reports/                       # 构建报告
│   └── build.log                  # 编译日志
├── packaging/                     # 预编译包
│   └── haproxy-3.2.0-ohos-aarch64.tar.gz
├── manifest.yaml                  # 构建清单
└── README.md                      # 本文档
```

## 技术支持

如遇问题，请查阅：
- 构建日志: `reports/build.log`
- 清单文件: `manifest.yaml`
- 官方文档: https://www.haproxy.org/