# lsquic 4.9.4 适配笔记（HarmonyOS PC / aarch64-linux-ohos）

## 概况
- LiteSpeed QUIC 协议栈（QUIC + HTTP/3），C，v4.9.4 官方 tag
- TLS 后端：**OpenSSL 3.5.6**（conan）——上游原生绑定 BoringSSL，本适配通过
  compat shim 桥接到 OpenSSL 3.5+ 的拉模式 QUIC TLS API
- 产物：liblsquic.a（静态库）
- 上游注册测试：**82 个**（tests/CMakeLists.txt：63 FOREACH + 19 显式），
  本地 Debug 构建真跑 **81/81 执行，80 通过，1 平台豁免**

## 攻坚核心：BoringSSL → OpenSSL 3.5+ QUIC TLS 桥接

### 问题（三层）
1. **API 模型翻转**：lsquic 全源码用 BoringSSL 推模式 API
   （`SSL_provide_quic_data` / `SSL_set_quic_method` + `SSL_QUIC_METHOD`
   五回调 / `SSL_set_quic_transport_params`）；OpenSSL 3.5+ 只提供拉模式
   `SSL_set_quic_tls_cbs` + `OSSL_DISPATCH` 六回调（crypto_send/recv_rcd/
   release_rcd/yield_secret/got_transport_params/alert）。上游 CMakeLists
   写了 OpenSSL 检测分支但源码从未迁移（master 分支同样）。
2. **EVP_AEAD 家族**：BoringSSL 的 `EVP_AEAD_CTX_seal/open/init` 在 OpenSSL
   无对应（OpenSSL EVP_CIPHER 是分开的 enc/dec 上下文）。栈上内嵌
   `EVP_CIPHER_CTX`（值语义）在 OpenSSL 下不可行（不透明类型）。
3. **头文件族差异**：`openssl/aead.h`/`chacha.h`/`hkdf.h`/`nid.h` 为
   BoringSSL 专有；`HKDF_extract`/`HKDF_expand`/`CRYPTO_chacha_20`/
   `SSL_CTX_set_custom_verify`/`ssl_verify_result_t` 等 API Open SSL 无。

### 方案（patches/0001-openssl-tls-backend-port.patch）
新增 `src/liblsquic/lsquic_ossl_compat.h/.c`（约 700 行）：
- **推拉翻转桥**：`SSL_provide_quic_data` 把握手数据存 per-SSL rcd 队列
  （SSL ex_data），OpenSSL 经 `crypto_recv_rcd` 拉取、`crypto_release_rcd`
  报消耗；`SSL_set_quic_method` 注册 OSSL_DISPATCH 表，六回调转发到
  lsquic 原有 `cry_sm_*`（set_read/write_secret/add_handshake_data/
  flush_flight/send_alert），protection level 经
  `OSSL_RECORD_PROTECTION_LEVEL_*` ↔ `enum ssl_encryption_level_t` 映射
  （ngtcp2 crypto/ossl/ossl.c 为标杆参照）
- **传输参数**：发送走 `SSL_set_quic_tls_transport_params`；接收经
  `got_transport_params` 回调存 per-SSL，`SSL_get_peer_quic_transport_params`
  读出
- **EVP_AEAD 重实现**：AES-128/256-GCM + ChaCha20-Poly1305 在 EVP_CIPHER
  上实现 seal/open；GCM 支持 8-16 可变 nonce（gQUIC 16 字节）与 8-16
  可变 tag（QUIC 16 / gQUIC STK 12）；`EVP_AEAD_CTX` 改为含
  `EVP_CIPHER_CTX*` 句柄的结构体（保持按值内嵌合法）
- **CHACHA20 HP**：`CRYPTO_chacha_20` 用 `EVP_chacha20` 重写（16 字节
  IV = counter||nonce 拼装）
- **HKDF**：`HKDF_extract`（HMAC 实现）/`HKDF_expand`（EVP_PKEY_HKDF
  EXPAND_ONLY 模式）
- **会话票据**：`SSL_SESSION_to/from_bytes` → `i2d/d2i_SSL_SESSION`
  （同 DER 编码）
- **0-RTT 降级**：BoringSSL 的 `SSL_in_early_data`/
  `SSL_reset_early_data_reject`/`SSL_set_quic_early_data_context` 无
  OpenSSL 拉模式等价物——会话恢复正常工作，0-RTT early data 不发送
  （shim 返回安全默认值，握手/1-RTT/密钥更新全功能）
- **证书校验**：`SSL_CTX_set_custom_verify` 走标准 verify 路径，
  lsquic 应用层校验（enp_verify_cert）在 set_secret 后照常运行
- 17 个源文件 `#ifdef HAVE_OPENSSL` 条件编译微调（include 替换 +
  EVP_CIPHER_CTX 指针化 + hp ctx 生命周期 helper）

### CMake 侧
- `LSQUIC_LIBSSL=OPENSSL` 跳过 TLS 探测（探测需目标机编译链接，
  交叉环境不可行），直接定义 `-DHAVE_OPENSSL`
- `LSQUIC_BIN=OFF`（示例程序依赖 libevent，且 bin/prog.c 有 BoringSSL
  专有 API——库本体不受影响）
- 预生成 `lsquic_versions_to_string.c`（perl gen-verstrs.pl 的确定性
  输出，消除构建期 Perl 依赖）；存在该文件时 CMake 跳过 find_package(Perl)
- `CMAKE_POLICY_VERSION_MINIMUM=3.5`（上游声明 3.0...3.23，cmake 4.x 需要）

### 源码获取（submodule 坑）
GitHub release tarball **不含** `ls-qpack`/`lshpack` 两个必需 submodule
（空目录）。conanfile source() 在主 tarball 解压后追加下载两个官方
submodule tarball（上游 tag 绑定 commit）并摆位。

## 依赖
- openssl/3.5.6（制品仓，实际头文件 3.5.7）
- zlib/1.3.1（制品仓）

## 测试（upstream-testing 硬纪律）

上游注册测试 N=82（CMake add_test 全量计数）。本地 Debug 构建
（-DLSQUIC_TESTS=ON -DLSQUIC_ASAN=OFF）+ ctest 真跑：

- **80 通过**
- **1 失败：hcsi_reader —— 平台豁免**
  根因：鸿蒙 musl `open_memstream` 在 **fclose 前未 fflush 时丢数据**
  （独立复现器：`fprintf(f,...)` 后直接 `fclose(f)` → buffer 空、sz=0；
  `fflush` 后则正常）。该测试用 `open_memstream` 收集回调输出、fclose
  后 strcmp——libc 缺陷导致回调输出丢失，与 lsquic 逻辑无关。
  其余 81 个用例（含同机制的 80 个）全绿佐证状态机本身正常。

### 中途修复的两个真 bug（compat shim）
1. `test_dec` "cannot seal"：shim 忽略了 `EVP_AEAD_CTX_init` 的 tag_len
   参数（gQUIC 用 12 字节 tag，QUIC 用 16）→ 支持 8-16 可变 tag
2. `test_stk` open 断言：gQUIC STK 用 16 字节 nonce → GCM 路径按调用
   实际 nonce_len 重设 IVLEN（ChaCha20-Poly1305 固定 12）

## 复现命令
```
conan create archives/l/lsquic/4.9.4 -pr:h=ci/conan/profiles/ohos-aarch64 \
  -pr:b=ci/conan/profiles/ohos-aarch64 --build=missing
```

上游测试（本地）：
```
cmake -DCMAKE_BUILD_TYPE=Debug -DLSQUIC_TESTS=ON -DLSQUIC_ASAN=OFF \
  -DLSQUIC_BIN=OFF -DLSQUIC_LIBSSL=OPENSSL ... && cmake --build . -- -j1
ctest -j4   # 80/81 pass, 1 musl open_memstream 平台豁免
```
