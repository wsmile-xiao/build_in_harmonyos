// OHOS 专项测试 — picojson 1.3.0
// 在 OHOS aarch64 工具链（clang 15 + libc++17）下验证 picojson 的平台敏感行为：
//   1. int64 精确往返（超出 double 精确范围的大整数）
//   2. UTF-8 字符串解析与序列化往返
//   3. 畸形输入的错误处理（错误位置信息）
//   4. 浮点序列化格式（不依赖 locale 的稳定输出）
//   5. C++17 标准库交互（std::string_view 等）
#include <picojson.h>

#include <cmath>
#include <cstdio>
#include <cstring>
#include <string>
#include <string_view>

static int failures = 0;

#define CHECK(cond, msg)                                                   \
    do {                                                                   \
        if (!(cond)) {                                                     \
            std::printf("FAIL: %s\n", msg);                                \
            ++failures;                                                    \
        }                                                                  \
    } while (0)

int main() {
    // 1. int64 精确往返：超过 2^53 的整数在 double 中会丢精度
    {
        picojson::value v;
        const char* s = "9223372036854775807";  // INT64_MAX
        std::string err = picojson::parse(v, s, s + std::strlen(s));
        CHECK(err.empty(), "int64 parse no error");
#if PICOJSON_USE_INT64
        CHECK(v.is<int64_t>(), "int64 type detected");
        CHECK(v.get<int64_t>() == 9223372036854775807LL,
              "int64 value exact round-trip");
#else
        CHECK(v.is<double>(), "int64-as-double type");
        CHECK(v.get<double>() == 9.2233720368547758e+18,
              "int64-as-double value");
#endif
    }
    // 2. UTF-8 字符串往返（含多字节字符与转义）
    {
        picojson::value v;
        const std::string in = "{\"s\":\"\\u4f60\\u597d\\u0020\\u4e16\\u754c\"}";  // 你好 世界
        std::string err = picojson::parse(v, in);
        CHECK(err.empty(), "utf8 parse no error");
        const std::string decoded = v.get<picojson::object>()["s"].get<std::string>();
        CHECK(decoded == "\xe4\xbd\xa0\xe5\xa5\xbd \xe4\xb8\x96\xe7\x95\x8c",
              "utf8 escapes decoded correctly");
        picojson::value round;
        err = picojson::parse(round, v.serialize());
        CHECK(err.empty(), "utf8 re-parse after serialize");
        CHECK(round.serialize() == v.serialize(), "utf8 serialize stable");
    }
    // 3. 畸形输入错误处理（错误消息非空，且能继续使用库）
    {
        picojson::value v;
        const char* bad = "{\"a\":}";
        std::string err = picojson::parse(v, bad, bad + std::strlen(bad));
        CHECK(!err.empty(), "malformed json reports error");
        CHECK(err.find("line") != std::string::npos,
              "error message contains position info");
    }
    // 4. 浮点序列化：稳定格式、无 locale 依赖
    {
        picojson::value v(3.14159265358979);
        const std::string out = v.serialize();
        CHECK(out.find("3.14159") == 0, "double serialize stable prefix");
    }
    // 5. C++17 交互：从 string_view 构造并解析
    {
        std::string_view sv("[1,2,3]");
        picojson::value v;
        const char* begin = sv.data();
        const char* end = sv.data() + sv.size();
        std::string err = picojson::parse(v, begin, end);
        CHECK(err.empty(), "string_view parse no error");
        CHECK(v.is<picojson::array>() && v.get<picojson::array>().size() == 3,
              "array parsed from string_view");
    }
    if (failures == 0) {
        std::printf("ohos-picojson-test: ALL PASS\n");
        return 0;
    }
    std::printf("ohos-picojson-test: %d FAILURE(S)\n", failures);
    return 1;
}
