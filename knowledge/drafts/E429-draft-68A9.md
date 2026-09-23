# E429 — ohpcd `libcurl/8.5.0` 无 TLS 后端，需 HTTPS 的消费方必须改用 `curl/8.15.0.x`

## 错误特征
构建期一切正常（`configure` 只探测 `curl_easy_strerror`），故障延后到运行期：

```
Error: unsupported protocol scheme (281)          # CURLE_UNSUPPORTED_PROTOCOL
curl: (35) PEER did not return a valid message    # 或 TLS 握手相关失败
```

## 触发条件
- 构建系统: conan（任意 autotools/cmake 消费方）
- 阶段: requirements 选型 → runtime
- 前提: 依赖声明选了 `libcurl/8.5.0`，且程序需要 `https://`/`ftps://` 等 TLS 传输

## 根因分析
制品仓同时存在两个 curl 配方，二者的 pkg-config 模块名同为 `libcurl`：

| 包 | `CURL_USE_OPENSSL` | 传递依赖 | TLS 可用 |
|---|---|---|---|
| `libcurl/8.5.0` | `"OFF"`（其 recipe `generate()` 写死） | 仅 `zlib/1.3.1.1` | ❌ |
| `curl/8.15.0.x` | `True`（并显式取 `libssl.a`/`libcrypto.a`） | `openssl/3.5.6.1` + `zlib/1.3.1.1` | ✅ |

按包名误选 `libcurl/8.5.0` 后，二进制里根本没有 TLS 传输层；由于 `curl-config`/`pkg-config`
都会正常应答，探测宏无法发现，问题只在真实发起 TLS 请求时暴露。

## 推荐方案
1. `self.requires("curl/8.15.0.1")`，不要用 `libcurl/8.5.0`。
2. 在 test_package 里同时断言 **编译期与运行期** curl 版本，并确认 TLS 后端被链入。
   pianod2 的 `pianod -v -v` 会打印：
   ```
   SSL package: OpenSSL
     curl compile version 8.15.0
     curl runtime version 8.15.0
   ```
3. 通用校验命令：`strings <lib>/libcurl.a | grep -c OpenSSL`，或 `ldd` 目标二进制看是否引入 ssl/crypto。

## 影响范围
所有需要 HTTPS 的消费方（首例：pianod2 的 Pandora source，`pandoracomm.cpp:167` 拼接
`https://<rpc_host>/services/json/`）。
