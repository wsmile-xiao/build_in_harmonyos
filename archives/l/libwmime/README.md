# libwmime (VMime Mail Library)

> C++ library for RFC 5322 / MIME messages and IMAP, POP3, SMTP.

## 简介

libwmime 是 grommunio/wmime（VMime 分支）的发版形态，提供 RFC 5322 / MIME
消息的解析、构造与修改，以及 IMAP、POP3、SMTP、maildir、sendmail 等消息
收发能力，附带 TLS 与字符集转换支持。本适配对应上游 tag `wmime-1.1.0`，
CMake 构建，C++17，库目标 `wmime`（SOVERSION 2），无源码补丁。

## OHOS 适配要点

- TLS 后端固定为 `openssl`（依赖已发布的 openssl/3.5.8.1），不用上游默认的 gnutls；
- 字符集转换固定为 `iconv`（依赖已发布的 libiconv/1.17）；
- SASL 支持关闭（gsasl 尚无可用配方），IMAP/SMTP 的 SASL 认证路径不可用；
- 上游 CppUnit 套件通过 `VMIME_BUILD_TESTS=ON` 打开，build() 内以 `ctest` 真实执行。

## 依赖

| 依赖 | 版本 | 说明 |
|------|------|------|
| openssl | 3.5.8.1 | TLS 后端，已发布 |
| libiconv | 1.17 | 字符集转换，已发布 |
| cppunit | 1.15.1 | 仅 test_requires，用于上游测试，已发布 |

## 功能验证

```bash
conan create archives/l/libwmime/1.1.0 -pr:h=ci/conan/profiles/ohos-aarch64 -pr:b=ci/conan/profiles/ohos-aarch64
```

预期日志含 `HMBS_UPSTREAM_TEST_RESULT`（ctest）与
`HMBS_TEST_PACKAGE_RESULT`（2 个消费者用例）两行机器标记。

## 参考

- [上游仓库](https://github.com/grommunio/wmime)
- [VMime 原项目](https://github.com/kisli/vmime)
