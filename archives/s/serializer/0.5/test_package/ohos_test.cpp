// HarmonyOS 专项测试 for serializer 0.5.
// 独立于消费者测试 serializer_test：本用例验证 OHOS aarch64 平台特有行为——
// 字节序/内存布局、容器大小前缀（size_is）、C++17 optional/variant 分支与
// polymorphic 8 字节序列化 ID——全部在 OHOS 工具链下编译并真实运行。
#include <cstdint>
#include <iostream>
#include <memory>
#include <optional>
#include <string>
#include <variant>
#include <vector>

#include <serializer.h>

namespace {

int check(bool condition, const char* description) {
    if (condition) {
        return 0;
    }
    std::cerr << "FAIL: " << description << '\n';
    return 1;
}

// Polymorphic 基础类型：派生类型 zpp_ohos_payload 注册为 "zpp_ohos_payload"。
class zpp_ohos_payload : public zpp::serializer::polymorphic {
public:
    virtual ~zpp_ohos_payload() = default;
    virtual std::uint64_t tag() const = 0;
};

class zpp_ohos_payload_impl : public zpp_ohos_payload {
public:
    zpp_ohos_payload_impl() = default;
    explicit zpp_ohos_payload_impl(std::uint64_t v) noexcept : m_value(v) {}

    friend zpp::serializer::access;
    template <typename Archive, typename Self>
    static void serialize(Archive& archive, Self& self) {
        archive(self.m_value);
    }

    std::uint64_t tag() const override { return 0x3141592653589793ULL; }
    std::uint64_t value() const noexcept { return m_value; }

private:
    std::uint64_t m_value = 0;
};

namespace {
zpp::serializer::register_types<
    zpp::serializer::make_type<zpp_ohos_payload_impl,
                               zpp::serializer::make_id("zpp_ohos_payload")>>
    _;  // NOLINT
}  // namespace

}  // namespace

int main() {
    int failures = 0;

    // 1) aarch64 little-endian 字节布局：int32_t 42 -> 2a 00 00 00。
    {
        std::vector<unsigned char> data;
        zpp::serializer::memory_output_archive out(data);
        const std::int32_t value = 42;
        out(value);
        failures += check(data.size() == 4, "int32 serializes to exactly 4 bytes");
        failures += check(data[0] == 0x2a && data[1] == 0x00 && data[2] == 0x00 &&
                              data[3] == 0x00,
                          "int32 42 uses little-endian layout on aarch64");

        zpp::serializer::memory_input_archive in(data);
        std::int32_t restored = 0;
        in(restored);
        failures += check(restored == 42, "int32 round-trips");
    }

    // 2) size_is<std::uint16_t>：容器大小前缀为 2 字节。
    {
        std::vector<unsigned char> data;
        zpp::serializer::memory_output_archive out(data);
        std::vector<std::int32_t> v = {10, 20, 30};
        out(zpp::serializer::size_is<std::uint16_t>(v));
        failures += check(data.size() == 2 + 3 * 4,
                          "size_is<uint16_t> prepends 2-byte count");
        failures += check(data[0] == 3 && data[1] == 0,
                          "size prefix value is 3 (little-endian u16)");

        zpp::serializer::memory_input_archive in(data);
        std::vector<std::int32_t> restored;
        in(zpp::serializer::size_is<std::uint16_t>(restored));
        failures += check(restored == v, "size_is<uint16_t> round-trips");
    }

    // 3) C++17 optional / variant 往返（依赖于 __cplusplus >= 201703L 分支）。
    {
        std::vector<unsigned char> data;
        zpp::serializer::memory_output_archive out(data);
        zpp::serializer::memory_input_archive in(data);

        std::optional<std::string> opt = std::string("ohos-optional");
        out(opt);
        std::optional<std::string> restored_opt;
        in(restored_opt);
        failures += check(restored_opt.has_value(),
                          "std::optional loads as engaged");
        failures += check(*restored_opt == "ohos-optional",
                          "std::optional value preserved");

        std::variant<std::int32_t, std::string> var = std::string("ohos-variant");
        out(var);
        std::variant<std::int32_t, std::string> restored_var =
            std::int32_t{0};
        in(restored_var);
        failures += check(std::holds_alternative<std::string>(restored_var),
                          "std::variant alternative index preserved");
        failures += check(std::get<std::string>(restored_var) == "ohos-variant",
                          "std::variant value preserved");
    }

    // 4) polymorphic：8 字节序列化 ID 前缀 + 动态类型恢复。
    {
        std::vector<unsigned char> data;
        zpp::serializer::memory_output_archive out(data);
        zpp::serializer::memory_input_archive in(data);

        std::unique_ptr<zpp_ohos_payload> payload =
            std::make_unique<zpp_ohos_payload_impl>(0xDEADBEEFCAFEBABEULL);
        out(payload);
        // 8 字节 ID 前缀 + 8 字节成员值。
        failures += check(data.size() == 16,
                          "polymorphic object has 8-byte id prefix");

        std::unique_ptr<zpp_ohos_payload> restored;
        in(restored);
        failures += check(restored != nullptr,
                          "polymorphic object reconstructed via registry");
        failures += check(restored->tag() == 0x3141592653589793ULL,
                          "polymorphic dynamic type restored");
        failures += check(
            static_cast<zpp_ohos_payload_impl*>(restored.get())->value() ==
                0xDEADBEEFCAFEBABEULL,
            "polymorphic member value preserved");
    }

    if (failures != 0) {
        std::cerr << "serializer OHOS-specific test FAILED (" << failures
                  << " check(s))\n";
        return 1;
    }
    std::cout << "serializer OHOS-specific test PASSED\n";
    return 0;
}