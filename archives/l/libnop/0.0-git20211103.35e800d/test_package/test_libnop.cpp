// Consumer test for the header-only libnop package: include the installed
// headers and round-trip a representative set of types through the serializer
// and deserializer, including an error path.
#include <nop/serializer.h>
#include <nop/structure.h>
#include <nop/utility/stream_reader.h>
#include <nop/utility/stream_writer.h>

#include <cstdio>
#include <sstream>
#include <string>
#include <vector>

static int failures = 0;

#define CHECK(condition, message)                                        \
    do {                                                                 \
        if (condition) {                                                 \
            printf("  ok   %s\n", message);                              \
        } else {                                                         \
            printf("  FAIL %s\n", message);                              \
            failures++;                                                  \
        }                                                                \
    } while (0)

struct Point {
    int x{0};
    int y{0};
    std::string label;

    NOP_STRUCTURE(Point, x, y, label);
};

namespace {

template <typename T>
std::string Serialize(const T& value, bool* ok)
{
    nop::Serializer<nop::StreamWriter<std::stringstream>> serializer;
    *ok = static_cast<bool>(serializer.Write(value));
    return serializer.writer().stream().str();
}

template <typename T>
bool Deserialize(const std::string& data, T* value)
{
    nop::Deserializer<nop::StreamReader<std::stringstream>> deserializer{data};
    return static_cast<bool>(deserializer.Read(value));
}

template <typename T>
bool RoundTrip(const T& value, T* result)
{
    bool ok = false;
    const std::string data = Serialize(value, &ok);
    if (!ok)
        return false;
    return Deserialize(data, result);
}

}  // namespace

int main()
{
    printf("libnop consumer test\n");

    /* --- scalars and strings ------------------------------------------ */
    {
        int value = -123456789;
        int result = 0;
        CHECK(RoundTrip(value, &result) && result == value,
              "int32 round-trips through the serializer");

        std::string text = "native object protocols";
        std::string text_result;
        CHECK(RoundTrip(text, &text_result) && text_result == text,
              "std::string round-trips through the serializer");
    }

    /* --- containers ---------------------------------------------------- */
    {
        std::vector<int> values = { 1, 2, 3, 5, 8, 13, 21 };
        std::vector<int> result;
        CHECK(RoundTrip(values, &result) && result == values,
              "std::vector<int> round-trips through the serializer");
    }

    /* --- annotated structure ------------------------------------------- */
    {
        Point point{ 3, 4, "hypotenuse" };
        Point result;
        CHECK(RoundTrip(point, &result) && result.x == 3 && result.y == 4 &&
              result.label == "hypotenuse",
              "NOP_STRUCTURE annotated type round-trips");
    }

    /* --- optional values ----------------------------------------------- */
    {
        nop::Optional<std::string> engaged{ "present" };
        nop::Optional<std::string> engaged_result;
        CHECK(RoundTrip(engaged, &engaged_result) && engaged_result &&
              engaged_result.get() == "present",
              "engaged Optional round-trips");

        nop::Optional<std::string> empty;
        nop::Optional<std::string> empty_result{ "not empty" };
        CHECK(RoundTrip(empty, &empty_result) && !empty_result,
              "empty Optional round-trips as empty");
    }

    /* --- serialized form is deterministic ------------------------------ */
    {
        bool ok_a = false;
        bool ok_b = false;
        const std::string first = Serialize(std::string("stable"), &ok_a);
        const std::string second = Serialize(std::string("stable"), &ok_b);
        CHECK(ok_a && ok_b && !first.empty() && first == second,
              "serialization is deterministic and non-empty");
    }

    /* --- truncated input is reported as an error ----------------------- */
    {
        bool ok = false;
        const std::string data = Serialize(std::string("truncated payload"), &ok);
        std::string result;
        const std::string truncated = data.substr(0, data.size() / 2);
        CHECK(ok && !Deserialize(truncated, &result),
              "reading a truncated stream fails cleanly");
    }

    printf("consumer assertions: %d failed\n", failures);
    return failures == 0 ? 0 : 1;
}
