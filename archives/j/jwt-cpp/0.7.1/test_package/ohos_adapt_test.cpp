// ohos_adapt_test.cpp — jwt-cpp 0.7.1 HarmonyOS (OHOS) 专项适配测试
//
// 独立于上游测试，专门验证 jwt-cpp 在 OHOS aarch64 静态工具链
// (clang 15 / libc++ / 静态 libcrypto) 下的真实可用性：
//   1. 平台与编译器身份自检（OHOS aarch64）
//   2. HS256 / RS256 / ES256 三种算法签名 + 校验闭环（使用上游 Keys.cpp 真实密钥）
//   3. 过期 token 校验失败路径（token_verification_error::token_expired）
// 全部通过返回 0；任一失败打印 FAIL 并返回非 0。
#include <jwt-cpp/jwt.h>
#include <chrono>
#include <cstdio>
#include <string>

#if defined(__aarch64__)
#define OHOS_ARCH "aarch64"
#else
#define OHOS_ARCH "unknown"
#endif

// 真实密钥（来源：上游 tests/Keys.cpp，2026-09-02 提取）
static const std::string rsa_priv_key =
    R"(-----BEGIN PRIVATE KEY-----
MIIEvwIBADANBgkqhkiG9w0BAQEFAASCBKkwggSlAgEAAoIBAQC4ZtdaIrd1BPIJ
tfnF0TjIK5inQAXZ3XlCrUlJdP+XHwIRxdv1FsN12XyMYO/6ymLmo9ryoQeIrsXB
XYqlET3zfAY+diwCb0HEsVvhisthwMU4gZQu6TYW2s9LnXZB5rVtcBK69hcSlA2k
ZudMZWxZcj0L7KMfO2rIvaHw/qaVOE9j0T257Z8Kp2CLF9MUgX0ObhIsdumFRLaL
DvDUmBPr2zuh/34j2XmWwn1yjN/WvGtdfhXW79Ki1S40HcWnygHgLV8sESFKUxxQ
mKvPUTwDOIwLFL5WtE8Mz7N++kgmDcmWMCHc8kcOIu73Ta/3D4imW7VbKgHZo9+K
3ESFE3RjAgMBAAECggEBAJTEIyjMqUT24G2FKiS1TiHvShBkTlQdoR5xvpZMlYbN
tVWxUmrAGqCQ/TIjYnfpnzCDMLhdwT48Ab6mQJw69MfiXwc1PvwX1e9hRscGul36
ryGPKIVQEBsQG/zc4/L2tZe8ut+qeaK7XuYrPp8bk/X1e9qK5m7j+JpKosNSLgJj
NIbYsBkG2Mlq671irKYj2hVZeaBQmWmZxK4fw0Istz2WfN5nUKUeJhTwpR+JLUg4
ELYYoB7EO0Cej9UBG30hbgu4RyXA+VbptJ+H042K5QJROUbtnLWuuWosZ5ATldwO
u03dIXL0SH0ao5NcWBzxU4F2sBXZRGP2x/jiSLHcqoECgYEA4qD7mXQpu1b8XO8U
6abpKloJCatSAHzjgdR2eRDRx5PMvloipfwqA77pnbjTUFajqWQgOXsDTCjcdQui
wf5XAaWu+TeAVTytLQbSiTsBhrnoqVrr3RoyDQmdnwHT8aCMouOgcC5thP9vQ8Us
rVdjvRRbnJpg3BeSNimH+u9AHgsCgYEA0EzcbOltCWPHRAY7B3Ge/AKBjBQr86Kv
TdpTlxePBDVIlH+BM6oct2gaSZZoHbqPjbq5v7yf0fKVcXE4bSVgqfDJ/sZQu9Lp
PTeV7wkk0OsAMKk7QukEpPno5q6tOTNnFecpUhVLLlqbfqkB2baYYwLJR3IRzboJ
FQbLY93E8gkCgYB+zlC5VlQbbNqcLXJoImqItgQkkuW5PCgYdwcrSov2ve5r/Acz
FNt1aRdSlx4176R3nXyibQA1Vw+ztiUFowiP9WLoM3PtPZwwe4bGHmwGNHPIfwVG
m+exf9XgKKespYbLhc45tuC08DATnXoYK7O1EnUINSFJRS8cezSI5eHcbQKBgQDC
PgqHXZ2aVftqCc1eAaxaIRQhRmY+CgUjumaczRFGwVFveP9I6Gdi+Kca3DE3F9Pq
PKgejo0SwP5vDT+rOGHN14bmGJUMsX9i4MTmZUZ5s8s3lXh3ysfT+GAhTd6nKrIE
kM3Nh6HWFhROptfc6BNusRh1kX/cspDplK5x8EpJ0QKBgQDWFg6S2je0KtbV5PYe
RultUEe2C0jYMDQx+JYxbPmtcopvZQrFEur3WKVuLy5UAy7EBvwMnZwIG7OOohJb
vkSpADK6VPn9lbqq7O8cTedEHttm6otmLt8ZyEl3hZMaL3hbuRj6ysjmoFKx6CrX
rK0/Ikt5ybqUzKCMJZg2VKGTxg==
-----END PRIVATE KEY-----)";

static const std::string rsa_pub_key =
    R"(-----BEGIN PUBLIC KEY-----
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEAuGbXWiK3dQTyCbX5xdE4
yCuYp0AF2d15Qq1JSXT/lx8CEcXb9RbDddl8jGDv+spi5qPa8qEHiK7FwV2KpRE9
83wGPnYsAm9BxLFb4YrLYcDFOIGULuk2FtrPS512Qea1bXASuvYXEpQNpGbnTGVs
WXI9C+yjHztqyL2h8P6mlThPY9E9ue2fCqdgixfTFIF9Dm4SLHbphUS2iw7w1JgT
69s7of9+I9l5lsJ9cozf1rxrXX4V1u/SotUuNB3Fp8oB4C1fLBEhSlMcUJirz1E8
AziMCxS+VrRPDM+zfvpIJg3JljAh3PJHDiLu902v9w+Iplu1WyoB2aPfitxEhRN0
YwIDAQAB
-----END PUBLIC KEY-----)";

static const std::string ecdsa256_priv_key =
    R"(-----BEGIN PRIVATE KEY-----
MIGHAgEAMBMGByqGSM49AgEGCCqGSM49AwEHBG0wawIBAQQgPGJGAm4X1fvBuC1z
SpO/4Izx6PXfNMaiKaS5RUkFqEGhRANCAARCBvmeksd3QGTrVs2eMrrfa7CYF+sX
sjyGg+Bo5mPKGH4Gs8M7oIvoP9pb/I85tdebtKlmiCZHAZE5w4DfJSV6
-----END PRIVATE KEY-----)";

static const std::string ecdsa256_pub_key =
    R"(-----BEGIN PUBLIC KEY-----
MFkwEwYHKoZIzj0CAQYIKoZIzj0DAQcDQgAEQgb5npLHd0Bk61bNnjK632uwmBfr
F7I8hoPgaOZjyhh+BrPDO6CL6D/aW/yPObXXm7SpZogmRwGROcOA3yUleg==
-----END PUBLIC KEY-----)";

static int checks = 0;

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (!(cond)) {                                                       \
            std::fprintf(stderr, "FAIL: %s\n", msg);                         \
            return 1;                                                        \
        }                                                                    \
        ++checks;                                                            \
        std::printf("  [OK] %s\n", msg);                                     \
    } while (0)

int main() {
    std::printf("jwt-cpp 0.7.1 OHOS adaptation test\n");
    std::printf("  platform: OHOS, arch=%s, libcxx=libc++\n", OHOS_ARCH);
    CHECK(std::string(OHOS_ARCH) == "aarch64", "OHOS aarch64 target");

    using clock = std::chrono::system_clock;

    // 1) HS256
    {
        auto token = jwt::create()
                         .set_issuer("ohos-test")
                         .set_subject("adaptation")
                         .set_issued_at(clock::now())
                         .set_expires_at(clock::now() + std::chrono::hours(1))
                         .sign(jwt::algorithm::hs256{"ohos-secret"});
        auto decoded = jwt::decode(token);
        jwt::verify().allow_algorithm(jwt::algorithm::hs256{"ohos-secret"}).verify(decoded);
        CHECK(decoded.get_subject() == "adaptation", "HS256 sign+verify round-trip");
        CHECK(decoded.get_issuer() == "ohos-test", "HS256 issuer claim");
    }

    // 2) RS256
    {
        auto token = jwt::create()
                         .set_issuer("ohos-test")
                         .set_payload_claim("alg-check", jwt::claim(std::string("rs256")))
                         .sign(jwt::algorithm::rs256(rsa_pub_key, rsa_priv_key, "", ""));
        auto decoded = jwt::decode(token);
        jwt::verify().allow_algorithm(jwt::algorithm::rs256(rsa_pub_key, "", "", "")).verify(decoded);
        CHECK(decoded.get_payload_claim("alg-check").as_string() == "rs256", "RS256 sign+verify round-trip");
    }

    // 3) ES256
    {
        auto token = jwt::create()
                         .set_issuer("ohos-test")
                         .set_payload_claim("alg-check", jwt::claim(std::string("es256")))
                         .sign(jwt::algorithm::es256(ecdsa256_pub_key, ecdsa256_priv_key, "", ""));
        auto decoded = jwt::decode(token);
        jwt::verify().allow_algorithm(jwt::algorithm::es256(ecdsa256_pub_key, "", "", "")).verify(decoded);
        CHECK(decoded.get_payload_claim("alg-check").as_string() == "es256", "ES256 sign+verify round-trip");
    }

    // 4) 过期 token 校验失败路径
    {
        auto token = jwt::create()
                         .set_issuer("ohos-test")
                         .set_expires_at(clock::now() - std::chrono::hours(1))
                         .sign(jwt::algorithm::hs256{"ohos-secret"});
        auto decoded = jwt::decode(token);
        bool threw = false;
        try {
            jwt::verify().allow_algorithm(jwt::algorithm::hs256{"ohos-secret"}).verify(decoded);
        } catch (const jwt::error::token_verification_exception& e) {
            threw = (e.code() == jwt::error::token_verification_error::token_expired);
        }
        CHECK(threw, "expired token rejected (token_expired)");
    }

    std::printf("  RESULT: %d checks passed on OHOS\n", checks);
    return 0;
}
