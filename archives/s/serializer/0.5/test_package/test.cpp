// Consumer test for serializer 0.5.
// Uses only the installed public header (serializer.h) and the public
// zpp::serializer API: save/load round-trip of STL containers, a custom
// class and polymorphic dispatch.
#include <iostream>
#include <memory>
#include <string>
#include <vector>

#include <serializer.h>

namespace {

class point {
public:
    point() = default;
    point(int x, int y) noexcept : m_x(x), m_y(y) {}

    friend zpp::serializer::access;
    template <typename Archive, typename Self>
    static void serialize(Archive& archive, Self& self) {
        archive(self.m_x, self.m_y);
    }

    int get_x() const noexcept { return m_x; }
    int get_y() const noexcept { return m_y; }

private:
    int m_x = 0;
    int m_y = 0;
};

class command : public zpp::serializer::polymorphic {
public:
    virtual ~command() = default;
    virtual int kind() const = 0;
};

class sleep_command : public command {
public:
    sleep_command() = default;
    explicit sleep_command(int seconds) noexcept : m_seconds(seconds) {}

    friend zpp::serializer::access;
    template <typename Archive, typename Self>
    static void serialize(Archive& archive, Self& self) {
        archive(self.m_seconds);
    }

    int kind() const override { return 1; }
    int seconds() const noexcept { return m_seconds; }

private:
    int m_seconds = 0;
};

// Polymorphic serialization requires the derived type to be registered
// before it can be saved/loaded through its base (see upstream README).
namespace {
zpp::serializer::register_types<
    zpp::serializer::make_type<sleep_command,
                               zpp::serializer::make_id("sleep_command")>> _
    ;  // NOLINT
}  // namespace

int check(bool condition, const char* description) {
    if (condition) {
        return 0;
    }
    std::cerr << "FAIL: " << description << '\n';
    return 1;
}

}  // namespace

int main() {
    int failures = 0;

    // STL container round-trip.
    {
        std::vector<unsigned char> data;
        zpp::serializer::memory_output_archive out(data);
        zpp::serializer::memory_input_archive in(data);

        std::vector<int> original = {1, 2, 3, 4, 5};
        out(original);
        std::vector<int> restored;
        in(restored);

        failures += check(restored == original,
                          "vector round-trip preserves contents");
    }

    // Custom class round-trip.
    {
        std::vector<unsigned char> data;
        zpp::serializer::memory_output_archive out(data);
        zpp::serializer::memory_input_archive in(data);

        point p(7, 11);
        out(p);
        point restored;
        in(restored);

        failures += check(restored.get_x() == 7 && restored.get_y() == 11,
                          "custom class round-trip preserves fields");
    }

    // Polymorphic serialization through the registered base.
    {
        std::vector<unsigned char> data;
        zpp::serializer::memory_output_archive out(data);
        zpp::serializer::memory_input_archive in(data);

        std::unique_ptr<command> cmd = std::make_unique<sleep_command>(42);
        out(cmd);
        std::unique_ptr<command> restored;
        in(restored);

        failures += check(restored != nullptr,
                          "polymorphic round-trip reconstructs object");
        failures += check(restored->kind() == 1,
                          "polymorphic round-trip keeps dynamic type");
        failures += check(static_cast<sleep_command*>(restored.get())->seconds() == 42,
                          "polymorphic round-trip keeps member value");
    }

    if (failures != 0) {
        std::cerr << "serializer consumer test FAILED (" << failures
                  << " check(s))\n";
        return 1;
    }
    std::cout << "serializer consumer test PASSED\n";
    return 0;
}
