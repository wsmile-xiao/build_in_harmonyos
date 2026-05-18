# curl

curl 是一个命令行工具和库，用于传输数据，支持多种协议。

## 描述
curl 是一个开源的命令行工具和库，用于使用 URL 语法传输数据。支持 HTTP、HTTPS、FTP、FTPS 等多种协议。

## 已编译版本
- 8.15.0 (2025-07-16)

## 依赖
- OpenSSL 1.1.1w
- zlib 1.3.1

## 特性
- 支持多种协议：HTTP, HTTPS, FTP, FTPS, GOPHER, GOPHERS, DICT, FILE, IMAP, IMAPS, POP3, POP3S, RTSP, SMB, SMBS, SMTP, SMTPS, TELNET, TFTP, WS, WSS, IPFS, IPNS, MQTT
- SSL/TLS 支持（OpenSSL）
- 压缩支持（zlib）
- IPv6 支持
- 大文件支持

## 使用方法
```bash
# 基本用法
curl https://example.com

# 下载文件
curl -O https://example.com/file.txt

# POST 请求
curl -X POST -d "data" https://example.com/api
```

## 注意事项
- HTTPS 请求需要配置 CA 证书路径（使用 --cacert 或 CURLOPT_CAINFO）
