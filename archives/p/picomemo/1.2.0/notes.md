# picomemo 1.2.0 适配笔记

## 上游构成

- `omemo.c` / `omemo.h`：X3DH + Double Ratchet + OMEMO protobuf 的紧凑实现；
  发布包中已附带拆分生成的 `gen/omemo0.c`（OMEMO 0.3）与 `gen/omemo2.c`（OMEMO 0.9），
  因此**无需 Lua** 重新生成。
- 两套后端，构建期选择：
  - Curve25519/EdDSA：`hacl.c`（默认）或 `c25519.c`；
  - AEAD/KDF/HMAC：`openssl.c`（EVP）或 `mbedtls.c`。

## 本配方配置

- 曲线后端 = `hacl`，AEAD 后端 = `openssl`。
- 制品仓的 `openssl/3.5.8.1` 为**静态**（`no-shared`），因此 `libpicomemo.so.1.2.0`
  内嵌 crypto，运行时无需 `libcrypto.so` 路径。
- 产物为共享库 `lib/libpicomemo.so.1.2.0`（含 omemo0+omemo2 两组符号），
  `libpicomemo.so.1` 与 `libpicomemo.so` 为相对符号链接；头文件 `omemo.h`/`driver.h`/
  `gen/omemo0.h`/`gen/omemo2.h`。

## 测试

上游测试 = `test/omemo.c`，被 Makefile 编两次（OMEMO 0.3 与 OMEMO 0.9），
每份 16 个 `RunTest` 用例，合计 **32**。`build()` 内实跑两遍：
`o/test-omemo`、`o/test-omemo2`，各 **15/16** 通过。

- 唯一跳过的用例是 `TestSessionIntegration`：它需要 `o/msg.bin`——由**外部 XMPP
  OMEMO bot**（`test/initsession.py` + `slixmpp-omemo`，跑在 prosody 的 Docker 容器里）
  生成的消息样本，本环境不可得。补丁 `patches/0001-skip-xmpp-integration-test.patch`
  仅在该 fixture 缺失时守卫跳过该用例，其它用例照常运行。
- `test-xmpp`（TLS/XMPP 联网）同样不可运行。

## 真机验证

`conan create` 退出码 0；`o/test-omemo`、`o/test-omemo2` 各输出
`All tests succeeded`（15 个 `Finished test`）；`test_package` 消费者 10/10。
