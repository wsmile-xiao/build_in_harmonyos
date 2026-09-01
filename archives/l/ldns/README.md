# ldns

## 简介

ldns是一个简化DNS编程的C库，支持DNSSEC操作。

## 版本信息

- 版本: 1.9.0
- 发布日期: 2025-12-05
- 网站: https://www.nlnetlabs.nl/projects/ldns/

## 编译产物

- libldns.a (静态库)
- libldns.so.3.6.0 (动态库)
- drill: DNS查询工具
- ldns-config: 配置工具
- 示例工具: ldns-mx, ldns-notify, ldns-read-zone 等

## 依赖

- openssl/3.5.6

## 使用方法

```bash
ldns-drill name [@server] [type]
ldns-drill example.com @8.8.8.8 A
```

## Conan 使用

```bash
conan install --requires=ldns/1.9.0
```
