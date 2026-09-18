# lsquic

LiteSpeed QUIC (LSQUIC) Library — open-source implementation of QUIC and
HTTP/3 functionality for servers and clients (RFC 9000/9001/9002/9114).

- 上游：https://github.com/litespeedtech/lsquic
- 语言：C
- 构建系统：CMake
- TLS 后端：OpenSSL 3.5+（BoringSSL API 经 compat shim 桥接，见 4.9.4/notes.md）

## 版本索引

| 版本 | 状态 | 备注 |
|------|------|------|
| 4.9.4 | built | OpenSSL QUIC TLS 桥接（B 素材：QUIC+TLS 层跨库坑） |
