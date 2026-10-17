// ohos_adapt_test.cpp — cpp-jwt 1.5.1 HarmonyOS adaptation test.
// Covers platform identity, none/HS384/HS512 algorithms, add/remove claims,
// header fields and the expired-token failure path. Prints one line per
// check; any failure prints FAIL and exits non-zero.
#include <chrono>
#include <cstdio>
#include <string>
#include <system_error>

#include "jwt/jwt.hpp"

#if defined(__aarch64__)
#define OHOS_ARCH "aarch64"
#else
#define OHOS_ARCH "unknown"
#endif

static int checks = 0;

#define CHECK(cond, msg)                              \
    do {                                              \
        if (!(cond)) {                                \
            std::fprintf(stderr, "FAIL: %s\n", msg); \
            return 1;                                 \
        }                                             \
        ++checks;                                     \
        std::printf("  [OK] %s\n", msg);             \
    } while (0)

int main() {
    using namespace jwt::params;

    std::printf("cpp-jwt 1.5.1 OHOS adaptation test\n");
    std::printf("  arch=%s\n", OHOS_ARCH);
    CHECK(std::string(OHOS_ARCH) == "aarch64", "OHOS aarch64 target");

    // 1) none algorithm round-trip (no secret needed).
    {
        jwt::jwt_object obj{headers({{"alg", "none"}, {"typ", "jwt"}}),
                            payload({{"iss", "ohos-test"}})};
        std::error_code ec;
        std::string enc = obj.signature(ec);
        CHECK(!ec, "none algorithm encodes");
        auto dec = jwt::decode(enc, algorithms({"none"}), ec, verify(false));
        CHECK(!ec, "none algorithm decodes");
        CHECK(dec.has_claim("iss"), "none payload claim present");
    }

    // 2) HS384 / HS512 round-trips with distinct secrets.
    {
        std::error_code ec;
        jwt::jwt_object o384{algorithm("HS384"), secret("ohos-384-secret"),
                             payload({{"sub", "adapt"}})};
        std::string e384 = o384.signature(ec);
        CHECK(!ec, "HS384 encodes");
        auto d384 =
            jwt::decode(e384, algorithms({"HS384"}), ec,
                        secret("ohos-384-secret"), verify(true));
        CHECK(!ec, "HS384 verifies");
        CHECK(d384.payload().has_claim_with_value("sub", "adapt"),
              "HS384 claim value");
    }
    {
        std::error_code ec;
        jwt::jwt_object o512{algorithm("HS512"), secret("ohos-512-secret"),
                             payload({{"sub", "adapt"}})};
        std::string e512 = o512.signature(ec);
        CHECK(!ec, "HS512 encodes");
        auto d512 =
            jwt::decode(e512, algorithms({"HS512"}), ec,
                        secret("ohos-512-secret"), verify(true));
        CHECK(!ec, "HS512 verifies");
        CHECK(d512.payload().has_claim_with_value("sub", "adapt"),
              "HS512 claim value");
    }

    // 3) Claim add/remove helpers.
    {
        jwt::jwt_object obj{algorithm("HS256"), secret("s"),
                            payload({{"user", "admin"}})};
        obj.add_claim("role", "tester");
        CHECK(obj.has_claim("role"), "add_claim visible");
        obj.remove_claim("role");
        CHECK(!obj.has_claim("role"), "remove_claim effective");
    }

    // 4) Expired token must be rejected.
    {
        jwt::jwt_object obj{algorithm("HS256"), secret("s")};
        obj.add_claim("exp", std::chrono::system_clock::now() -
                                 std::chrono::seconds{60});
        std::error_code ec;
        std::string enc = obj.signature(ec);
        CHECK(!ec, "expired token encodes");
        auto dec = jwt::decode(enc, algorithms({"HS256"}), ec, secret("s"),
                               verify(true));
        (void)dec;
        CHECK(static_cast<bool>(ec), "expired token rejected");
        CHECK(ec.value() ==
                  static_cast<int>(jwt::VerificationErrc::TokenExpired),
              "expired reason is TokenExpired");
    }

    std::printf("  RESULT: %d checks passed on OHOS\n", checks);
    return 0;
}
