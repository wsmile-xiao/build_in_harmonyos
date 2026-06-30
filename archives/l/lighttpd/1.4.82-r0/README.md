# lighttpd 1.4.82-r0 编译产物

## 编译信息

- **软件**: lighttpd
- **版本**: 1.4.82-r0
- **来源**: Alpine Linux (🅰)
- **编译日期**: 2026-05-23
- **目标平台**: OpenHarmony aarch64

## 编译产物

### 主程序

- `bin/lighttpd` - Web服务器主程序 (580KB)
- `bin/lighttpd-angel` - 守护进程管理器 (6KB)

### 模块

共 19 个模块，位于 `lib/lighttpd/`:

| 模块 | 功能 |
|------|------|
| mod_openssl.so | SSL/TLS 支持 |
| mod_deflate.so | 响应压缩 |
| mod_h2.so | HTTP/2 支持 |
| mod_proxy.so | 反向代理 |
| mod_fastcgi.so | FastCGI |
| mod_scgi.so | SCGI |
| mod_cgi.so | CGI |
| mod_auth.so | 认证 |
| mod_status.so | 状态监控 |
| mod_webdav.so | WebDAV |
| 等... | |

## 依赖

- openssl 1.1.1w
- pcre2 10.42
- zlib 1.3.1

## 编译配置

使用 meson 构建系统，配置选项：
- `-Dwith_openssl=true` (SSL/TLS 支持)
- `-Dwith_pcre2=true` (正则表达式 URL 重写)
- `-Dwith_zlib=enabled` (压缩支持)
- `-Dbuildtype=release` (优化编译)

## 平台适配

无需补丁，使用标准 meson 构建流程。

## 使用方法

```bash
# 启动服务器
lighttpd -f /path/to/lighttpd.conf

# 测试配置
lighttpd -t -f /path/to/lighttpd.conf

# 查看版本
lighttpd -v

# 查看编译特性
lighttpd -V
```

## 预编译包

完整预编译包：`lighttpd-1.4.82-ohos-aarch64.tar.gz` (1.0MB)

SHA256: 3a5d6a2029101b95e7c9058fcbbad33f7f53c24e3bd1cc8448bb1da39baf1576
