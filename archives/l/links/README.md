# links

Links 是一个文本模式的 Web 浏览器，支持表格、框架、SSL 加密连接等功能。

## 描述

Links 是 Lynx 的增强版，支持 HTTP、HTTPS、FTP 等协议。相比 Lynx，Links 支持更多 HTML 特性，包括表格和框架渲染。也提供图形模式（需要 SVGALIB 或 X Window）。

## 已编译版本
- 2.30 (2026-05-26)

## 依赖
- OpenSSL 3.x
- zlib
- brotli

## 特性
- HTTP/HTTPS 协议支持
- FTP 协议支持
- SSL/TLS 加密连接
- 表格和框架渲染
- 书签管理
- 下载管理
- 支持代理服务器

## 使用方法
```bash
# 打开网页
links https://example.com

# 查看版本
links -version
```

## 注意事项
- HTTPS 需要配置 CA 证书路径
- 默认以文本模式运行，`-g` 可切换到图形模式