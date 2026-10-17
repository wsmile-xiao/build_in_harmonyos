# libjose

C-language implementation of Javascript Object Signing and Encryption
(JOSE: JWK/JWS/JWE),上游为 latchset/jose。提供 `libjose` 共享库与 `jose`
命令行工具,覆盖 JWK 生成/加解密、JWS 签名验签、JWE 加解密与 DEF 压缩。

## OHOS 适配
- Meson 构建系统;`docs=disabled` 跳过 asciidoc man 页。
- 运行时依赖 jansson (JSON)、openssl/libcrypto (密码学后端)、zlib (JWE zip 压缩)。
- ohpcd openssl 配方不直接提供 libcrypto.pc,配方在 generate() 内派生别名。
- 共享库版本别名链 (libjose.so -> libjose.so.0 -> libjose.so.0.0.0) 物化为实体拷贝,适配 HMDFS。
- 上游 `meson test` 25 项在 build() 内完整执行;test_package 另有 8 断言消费者测试。

## 依赖
- jansson/2.15.1.1
- openssl/3.5.6
- zlib/1.3.1

## 参考
- 上游仓库: https://github.com/latchset/jose
- 源码包: https://github.com/latchset/jose/releases/download/v14/jose-14.tar.xz
