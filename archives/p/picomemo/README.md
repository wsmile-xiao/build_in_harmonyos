# picomemo — XMPP OMEMO 端到端加密密码学库

`picomemo` 是 XMPP 的 **OMEMO** 端到端加密所需密码学的紧凑、可移植实现
（X3DH + Double Ratchet + OMEMO protobuf 消息），不依赖 libsignal / libolm 代码。
同时支持 **OMEMO 0.3**（`eu.siacs.conversations.axolotl`）与 **OMEMO 0.9**
（`urn:xmpp:omemo:2`）。

## 产物

| 路径 | 说明 |
|------|------|
| `lib/libpicomemo.so.1.2.0` | 共享库（omemo0 + omemo2 两组符号），`libpicomemo.so.1` / `.so` 为符号链接 |
| `include/omemo.h` | 公共 API（默认 OMEMO 0.3，定义 `-DOMEMO2` 切 OMEMO 0.9） |
| `include/gen/omemo0.h`、`gen/omemo2.h` | 版本化拆分头 |
| `include/driver.h` | 密码学后端接口 |

## 密码学后端

构建期可选：

- 曲线原语：`hacl.c`（默认，HACL*，快且经形式化验证）或 `c25519.c`（低内存）；
- AEAD/KDF/HMAC：`openssl.c`（EVP，默认）或 `mbedtls.c`。

本包默认 `hacl` + `openssl`。制品仓 OpenSSL 为静态构建，故 `libpicomemo.so.1.2.0`
内嵌其密码学实现，运行时无需额外 `libcrypto.so`。

## 用法（OMEMO 0.3）

```c
struct omemoStore store;
omemoSetupStore(&store);
uint8_t buf[omemoGetSerializedStoreSize(&store)];
omemoSerializeStore(buf, &store);
```

详细 API 见 `omemo.h`。

## OHOS 适配要点

- 发布包已含 `gen/omemo0.c` / `gen/omemo2.c`，**无需 Lua**。
- OpenSSL 后端用 EVP_MAC / EVP_KDF（OpenSSL 3.x）。
- 上游 `test/omemo.c` 编两次（OMEMO 0.3 / 0.9）共 32 用例；`build()` 实跑 30，
  唯一未跑的 `TestSessionIntegration` 需要外部 XMPP OMEMO bot 生成的 `o/msg.bin` 样本。

## 参考资料

- 上游：<https://github.com/mierenhoop/picomemo>
- 许可证：ISC
