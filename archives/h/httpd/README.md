# Apache HTTP Server (httpd)

Apache HTTP Server 是世界上最流行的开源 Web 服务器软件，由 Apache 软件基金会开发和维护。

## 功能概述

- 模块化架构：支持动态加载模块扩展功能
- 虚拟主机：支持基于名称和基于 IP 的虚拟主机
- URL 重写：mod_rewrite 提供强大的 URL 重写功能
- 访问控制：支持基于主机、用户、组的访问控制
- SSL/TLS：mod_ssl 提供安全连接支持
- CGI/SSI：支持 CGI 脚本和服务器端包含

## OHOS 适配要点

### 平台识别

httpd 的 config.guess/config.sub 默认不支持 HarmonyOS，需要添加：
- `__OHOS__` LIBC 检测
- HarmonyOS 系统识别（`*-unknown-linux-ohos`）

### 依赖配置

需要显式指定依赖路径：
```bash
./configure --with-apr=$DEFAULT_PREFIX \
    --with-apr-util=$DEFAULT_PREFIX \
    --with-pcre=$DEFAULT_PREFIX/bin/pcre-config
```

### 已知问题

1. **config.status 临时目录**：HMDFS 权限限制可能导致临时目录创建失败，需使用固定目录绕过
2. **可选模块限制**：当前编译未启用 SSL、HTTP/2、LDAP 等可选模块

## 依赖关系

### 必需依赖

- apr (Apache Portable Runtime) - 可移植运行时库
- apr-util - APR 扩展工具库
- pcre - 正则表达式库

### 可选依赖

- openssl → mod_ssl (HTTPS 支持)
- zlib → mod_deflate (压缩支持)
- nghttp2 → mod_http2 (HTTP/2 支持)
- openldap → mod_authnz_ldap (LDAP 认证)

## 参考资料

- 官网：https://httpd.apache.org
- 源码：https://github.com/apache/httpd
- 文档：https://httpd.apache.org/docs/2.4/