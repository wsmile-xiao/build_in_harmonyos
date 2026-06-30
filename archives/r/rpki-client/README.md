# rpki-client

## 软件简介

rpki-client 是 OpenBSD 的 RPKI（Resource Public Key Infrastructure）验证工具移植版本。它用于：

- 验证 BGP 路由起源声明
- 下载并验证 RPKI 数据
- 生成 VRP（Validated ROA Payload）供 BGP 路由器使用

## 编译版本

| 版本 | 状态 | 编译日期 | 说明 |
|------|------|----------|------|
| 9.6 | published | 2026-06-11 | 手动编译，使用 LibreSSL |

## 依赖

### 运行时依赖
- LibreSSL 3.9.2（libcrypto, libssl, libtls）
- musl-fts 1.2.1（文件树遍历）
- expat 2.6.4（XML 解析）
- zlib 1.3.1（压缩）
- rsync 3.3.0（数据同步）

### 构建依赖
- LibreSSL 3.9.2（开发库）
- musl-fts 1.2.1
- clang 编译器

## 安装位置

- 二进制：`/usr/local/sbin/rpki-client`
- 配置：`/usr/local/etc/rpki/`（包含 5 个 RIR TAL 文件）

## 使用方法

```bash
# 验证版本
rpki-client -V

# 基本运行
rpki-client -d /var/cache/rpki -t /usr/local/etc/rpki

# 输出 VRP
rpki-client -j -o /var/db/rpki
```

## 平台适配说明

由于 HMDFS 文件系统限制，configure 无法创建临时文件，因此采用手动编译方式：

1. 手动创建 `config.h` 定义必要的宏
2. 手动编译源文件
3. 手动链接静态库（libcrypto.a, libssl.a, libtls.a, libfts.a）

## 相关资源

- 官方网站：https://rpki-client.org
- GitHub：https://github.com/rpki-client/rpki-client-portable
- 文档：https://man.openbsd.org/rpki-client
