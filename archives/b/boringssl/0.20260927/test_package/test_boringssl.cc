// test_package/test_boringssl.cc — R34 实质消费者测试 (boringssl/0.20260927)
//
// 本测试真实调用被测包 API（非空壳）：
//   1. 内存 BIO pair 上的 TLS 1.3 完整握手（含证书校验、应用数据双向收发）
//   2. BIGNUM 十进制大数运算（已知结果断言）
//   3. EVP_Digest SHA-256 已知向量（abc）
//   4. RAND_bytes 熵源
//
// 退出码：0 = 全部断言通过；1 = 存在失败。
#include <openssl/base.h>
#include <openssl/bio.h>
#include <openssl/bn.h>
#include <openssl/crypto.h>
#include <openssl/digest.h>
#include <openssl/evp.h>
#include <openssl/mem.h>
#include <openssl/pem.h>
#include <openssl/rand.h>
#include <openssl/ssl.h>
#include <openssl/x509.h>

#include <cstdint>
#include <cstdio>
#include <cstring>

namespace {

int g_checks = 0;
int g_failures = 0;

void Check(bool ok, const char *what) {
  ++g_checks;
  if (ok) {
    std::printf("ok %d - %s\n", g_checks, what);
  } else {
    std::printf("FAIL %d - %s\n", g_checks, what);
    ++g_failures;
  }
}

int ReadWithRetry(SSL *ssl, void *buf, int len) {
  for (int i = 0; i < 20; i++) {
    int r = SSL_read(ssl, buf, len);
    if (r > 0) {
      return r;
    }
    int err = SSL_get_error(ssl, r);
    if (err != SSL_ERROR_WANT_READ && err != SSL_ERROR_WANT_WRITE) {
      return r;
    }
  }
  return -1;
}

// 自签名测试证书（ECDSA P-256，CN=boringssl-ohos-test，有效期至 2046）。
const char kCertPem[] =
    "-----BEGIN CERTIFICATE-----\n"
    "MIIBgDCCASagAwIBAgIUPaUzvSeF9Ij+qQZeiNxRw9rXZQ4wCgYIKoZIzj0EAwIw\n"
    "HjEcMBoGA1UEAwwTYm9yaW5nc3NsLW9ob3MtdGVzdDAeFw0yNjA5MjcxNzI0Mzda\n"
    "Fw00NjA5MjIxNzI0MzdaMB4xHDAaBgNVBAMME2JvcmluZ3NzbC1vaG9zLXRlc3Qw\n"
    "WTATBgcqhkjOPQIBBggqhkjOPQMBBwNCAARHuZWxOd4VmjhzxsnD1raXEyjWFuXm\n"
    "aOL74f8lYWJh9GjFkUjfQs9uujU7z8wOQB3Gyd5Zt0gdpeY/QIiwJMU2o0IwQDAP\n"
    "BgNVHRMBAf8EBTADAQH/MA4GA1UdDwEB/wQEAwIChDAdBgNVHQ4EFgQUhDX0W1tY\n"
    "rFbjBo1VBD9i/I5kGXowCgYIKoZIzj0EAwIDSAAwRQIhAN03ygmZBuhpC4tS7fkH\n"
    "NFX8uk4ZeDiNqfTXp4EKfcLzAiBuqWRLGHyid8f3NQoOpeVi5oZWF68eNHJgrHbx\n"
    "xsrOOA==\n"
    "-----END CERTIFICATE-----\n";

const char kKeyPem[] =
    "-----BEGIN EC PRIVATE KEY-----\n"
    "MHcCAQEEIFEE9599jja0AT8G6H6Vay1llzFOCoyxuelJQpyIK5QgoAoGCCqGSM49\n"
    "AwEHoUQDQgAER7mVsTneFZo4c8bJw9a2lxMo1hbl5mji++H/JWFiYfRoxZFI30LP\n"
    "bro1O8/MDkAdxsneWbdIHaXmP0CIsCTFNg==\n"
    "-----END EC PRIVATE KEY-----\n";

}  // namespace

int main() {
  std::printf("== R34 consumer test: boringssl TLS/crypto API ==\n");

  // ---- 1. 版本标识 ----
  const char *version = OpenSSL_version(OPENSSL_VERSION);
  Check(version != nullptr && std::strcmp(version, "BoringSSL") == 0,
        "OpenSSL_version() reports BoringSSL");

  // ---- 2. BIGNUM 运算（已知结果） ----
  BIGNUM *a = nullptr, *b = nullptr, *sum = nullptr;
  Check(BN_dec2bn(&a, "12345678901234567890") > 0, "BN_dec2bn(a)");
  Check(BN_dec2bn(&b, "98765432109876543210") > 0, "BN_dec2bn(b)");
  sum = BN_new();
  Check(sum != nullptr, "BN_new()");
  Check(BN_add(sum, a, b) == 1, "BN_add(a, b)");
  char *sum_dec = BN_bn2dec(sum);
  Check(sum_dec != nullptr &&
            std::strcmp(sum_dec, "111111111011111111100") == 0,
        "BN_add result == 111111111011111111100");
  OPENSSL_free(sum_dec);
  BN_free(a);
  BN_free(b);
  BN_free(sum);

  // ---- 3. SHA-256 已知向量（abc） ----
  uint8_t md[EVP_MAX_MD_SIZE];
  unsigned md_len = 0;
  Check(EVP_Digest("abc", 3, md, &md_len, EVP_sha256(), nullptr) == 1,
        "EVP_Digest(SHA-256)");
  char hex[EVP_MAX_MD_SIZE * 2 + 1];
  for (unsigned i = 0; i < md_len && i < EVP_MAX_MD_SIZE; i++) {
    std::snprintf(hex + i * 2, 3, "%02x", md[i]);
  }
  Check(md_len == 32 &&
            std::strcmp(hex,
                        "ba7816bf8f01cfea414140de5dae2223b00361a396177a9cb410"
                        "ff61f20015ad") == 0,
        "SHA-256(\"abc\") known vector");

  // ---- 4. RAND_bytes ----
  uint8_t rnd[32] = {0};
  Check(RAND_bytes(rnd, sizeof(rnd)) == 1, "RAND_bytes()");
  bool nonzero = false;
  for (size_t i = 0; i < sizeof(rnd); i++) {
    nonzero = nonzero || rnd[i] != 0;
  }
  Check(nonzero, "RAND_bytes() output non-zero");

  // ---- 5. 内存 TLS 1.3 握手 + 应用数据（真实 API 依赖） ----
  X509 *cert = nullptr;
  EVP_PKEY *key = nullptr;
  {
    BIO *bio = BIO_new_mem_buf(kCertPem, -1);
    cert = PEM_read_bio_X509(bio, nullptr, nullptr, nullptr);
    BIO_free(bio);
    bio = BIO_new_mem_buf(kKeyPem, -1);
    key = PEM_read_bio_PrivateKey(bio, nullptr, nullptr, nullptr);
    BIO_free(bio);
  }
  Check(cert != nullptr && key != nullptr, "parse embedded test cert/key");

  SSL_CTX *sctx = SSL_CTX_new(TLS_method());
  SSL_CTX *cctx = SSL_CTX_new(TLS_method());
  Check(sctx != nullptr && cctx != nullptr, "SSL_CTX_new() server+client");
  Check(SSL_CTX_use_certificate(sctx, cert) == 1, "SSL_CTX_use_certificate");
  Check(SSL_CTX_use_PrivateKey(sctx, key) == 1, "SSL_CTX_use_PrivateKey");
  Check(SSL_CTX_check_private_key(sctx) == 1, "SSL_CTX_check_private_key");
  Check(SSL_CTX_set_min_proto_version(cctx, TLS1_3_VERSION) == 1,
        "client min proto = TLS 1.3");
  Check(SSL_CTX_set_min_proto_version(sctx, TLS1_3_VERSION) == 1,
        "server min proto = TLS 1.3");
  X509_STORE *store = SSL_CTX_get_cert_store(cctx);
  Check(store != nullptr && X509_STORE_add_cert(store, cert) == 1,
        "client trusts embedded self-signed cert");
  SSL_CTX_set_verify(cctx, SSL_VERIFY_PEER, nullptr);

  SSL *client = SSL_new(cctx);
  SSL *server = SSL_new(sctx);
  BIO *cbio = nullptr, *sbio = nullptr;
  Check(client != nullptr && server != nullptr &&
            BIO_new_bio_pair(&cbio, 0, &sbio, 0) == 1,
        "SSL_new() + BIO_new_bio_pair()");
  SSL_set_bio(client, cbio, cbio);
  SSL_set_bio(server, sbio, sbio);
  SSL_set_connect_state(client);
  SSL_set_accept_state(server);

  bool c_done = false, s_done = false;
  int stalled = 0;
  for (int i = 0; i < 200 && !(c_done && s_done); i++) {
    bool progressed = false;
    if (!c_done) {
      int r = SSL_do_handshake(client);
      if (r == 1) {
        c_done = true;
        progressed = true;
      } else {
        int err = SSL_get_error(client, r);
        if (err != SSL_ERROR_WANT_READ && err != SSL_ERROR_WANT_WRITE) {
          std::printf("client handshake error: %d\n", err);
          break;
        }
      }
    }
    if (!s_done) {
      int r = SSL_do_handshake(server);
      if (r == 1) {
        s_done = true;
        progressed = true;
      } else {
        int err = SSL_get_error(server, r);
        if (err != SSL_ERROR_WANT_READ && err != SSL_ERROR_WANT_WRITE) {
          std::printf("server handshake error: %d\n", err);
          break;
        }
      }
    }
    stalled = progressed ? 0 : stalled + 1;
    if (stalled > 20) {
      break;
    }
  }
  Check(c_done && s_done, "TLS 1.3 in-memory handshake completed");
  Check(SSL_version(client) == TLS1_3_VERSION, "client is using TLS 1.3");
  const SSL_CIPHER *cipher = SSL_get_current_cipher(client);
  Check(cipher != nullptr, "cipher negotiated");
  if (cipher != nullptr) {
    std::printf("    negotiated cipher: %s\n", SSL_CIPHER_get_name(cipher));
  }
  X509 *peer = SSL_get_peer_certificate(client);
  Check(peer != nullptr, "client received server certificate");
  X509_free(peer);

  static const char kPayload[] = "boringssl-ohos-consumer-e2e";
  int written = SSL_write(client, kPayload, (int)sizeof(kPayload));
  Check(written == (int)sizeof(kPayload), "SSL_write(c->s) payload");
  char rbuf[128] = {0};
  int read = ReadWithRetry(server, rbuf, sizeof(rbuf));
  Check(read == (int)sizeof(kPayload) &&
            std::memcmp(rbuf, kPayload, sizeof(kPayload)) == 0,
        "SSL_read(s) round-trip payload");

  static const char kPong[] = "pong-from-server";
  int pong_written = SSL_write(server, kPong, (int)sizeof(kPong));
  Check(pong_written == (int)sizeof(kPong), "SSL_write(s->c) payload");
  char cbuf[128] = {0};
  int pong_read = ReadWithRetry(client, cbuf, sizeof(cbuf));
  Check(pong_read == (int)sizeof(kPong) &&
            std::memcmp(cbuf, kPong, sizeof(kPong)) == 0,
        "SSL_read(c) round-trip payload");

  SSL_free(client);
  SSL_free(server);
  SSL_CTX_free(sctx);
  SSL_CTX_free(cctx);
  X509_free(cert);
  EVP_PKEY_free(key);

  std::printf("R34 consumer test: %d/%d assertions passed\n",
              g_checks - g_failures, g_checks);
  if (g_failures != 0) {
    std::printf("R34_RESULT=FAIL\n");
    return 1;
  }
  std::printf("R34_RESULT=PASS\n");
  return 0;
}
