# whois

## 软件描述

whois 是一个用于查询域名注册信息和互联网资源的客户端工具。

## 功能特点

- 查询域名的注册信息（ registrar、注册日期、到期日期等）
- 支持 RIPE-like 服务器的高级查询选项
- 支持国际化域名（IDN）通过 libidn2
- 配置文件支持自定义查询服务器

## 编译说明

whois 使用 Makefile 构建，不需要 configure 步骤。

### 构建步骤

```bash
# 生成 version.h
perl make_version_h.pl debian/changelog > version.h

# 编译
make whois prefix=$DEFAULT_PREFIX

# 安装
make install-whois prefix=$DEFAULT_PREFIX DESTDIR=$TEST_PREFIX
```

### 依赖

- libidn2（可选，用于国际化域名支持）

## 使用示例

```bash
# 查询域名信息
whois example.com

# 查询 IP 地址信息
whois 8.8.8.8

# 使用特定服务器
whois -h whois.ripe.net example.com
```

## 版本历史

| 版本 | 编译日期 | 状态 |
|------|---------|------|
| 5.6.6 | 2026-05-28 | built |

## 注意事项

1. whois 查询需要网络连接
2. 某些 WHOIS 服务器可能限制查询频率
3. 建议安装 libidn2 以支持国际化域名查询
