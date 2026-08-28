#include <aws/crt/Api.h>
#include <aws/crt/DateTime.h>
#include <aws/crt/JsonObject.h>
#include <aws/crt/Types.h>
#include <aws/crt/UUID.h>
#include <aws/crt/checksum/CRC.h>

#include <cstdio>
#include <cstddef>
#include <cstdint>
#include <string>

static int g_failures = 0;

#define CHECK(cond, msg)                                                       \
    do {                                                                       \
        if (cond) {                                                            \
            std::printf("[PASS] %s\n", msg);                                   \
        } else {                                                               \
            std::printf("[FAIL] %s\n", msg);                                   \
            ++g_failures;                                                      \
        }                                                                      \
    } while (0)

int main()
{
    /* RAII runtime init: wires allocator, error lists, logging. */
    Aws::Crt::ApiHandle apiHandle;

    /* 1. DateTime wraps the real system clock. */
    const uint64_t nowMillis = Aws::Crt::DateTime::Now().Millis();
    CHECK(nowMillis > 1577836800000ull, "DateTime::Now() > 2020-01-01 UTC");

    /* 2. Base64 encode/decode round trip over 64 bytes (88 chars, padded). */
    Aws::Crt::Vector<uint8_t> payload;
    for (uint8_t i = 0; i < 64; ++i)
    {
        payload.push_back(i);
    }
    const Aws::Crt::String encoded = Aws::Crt::Base64Encode(payload);
    const Aws::Crt::Vector<uint8_t> decoded = Aws::Crt::Base64Decode(encoded);
    CHECK(encoded.size() == 88 && decoded == payload,
          "Base64Encode/Base64Decode round trip");

    /* 3. UUID canonical textual form 8-4-4-4-12: aws-c-common formats the
     * 16 random bytes as lowercase %02x groups with dashes at indices
     * 8/13/18/23 only (no RFC-4122 version/variant nibbles are stamped). */
    const Aws::Crt::String uuid = Aws::Crt::UUID().ToString();
    bool uuidFormatOk =
        uuid.size() == 36 && uuid[8] == '-' && uuid[13] == '-'
        && uuid[18] == '-' && uuid[23] == '-';
    if (uuidFormatOk)
    {
        for (Aws::Crt::String::size_type i = 0; i < uuid.size(); ++i)
        {
            if (i == 8 || i == 13 || i == 18 || i == 23)
            {
                continue;
            }
            const char c = uuid[i];
            const bool hexDigit = (c >= '0' && c <= '9') || (c >= 'a' && c <= 'f');
            if (!hexDigit)
            {
                uuidFormatOk = false;
                break;
            }
        }
    }
    CHECK(uuidFormatOk, "UUID canonical string format 8-4-4-4-12");

    /* 3b. Parsing the textual form back must reproduce it byte-for-byte. */
    const Aws::Crt::UUID reparsed(uuid);
    CHECK((bool)reparsed && reparsed.ToString() == uuid,
          "UUID parse/format round trip");

    /* 4. JsonObject parsing + typed accessors. */
    Aws::Crt::JsonObject json(R"({"hello":"ohos","n":42})");
    CHECK(json.WasParseSuccessful() && json.View().GetString("hello") == "ohos"
              && json.View().GetInt64("n") == 42,
          "JsonObject parse and typed accessors");

    /* 5. CRC32 / CRC32C standard check values for "123456789"
     * (hardware-accelerated paths dispatch inside ComputeCRC32*). */
    static const char data[] = "123456789";
    auto cursor = Aws::Crt::ByteCursorFromArray(
        reinterpret_cast<const uint8_t *>(data), sizeof(data) - 1);
    CHECK(Aws::Crt::Checksum::ComputeCRC32(cursor) == 0xCBF43926u,
          "CRC32 standard check value");
    CHECK(Aws::Crt::Checksum::ComputeCRC32C(cursor) == 0xE3069283u,
          "CRC32C standard check value");

    if (g_failures == 0)
    {
        std::printf("aws-crt test_package: ALL CHECKS PASSED\n");
        return 0;
    }
    std::fprintf(stderr, "aws-crt test_package: %d check(s) FAILED\n", g_failures);
    return 1;
}
