// Consumer test for enchantum 0.4.0 — exercises the packaged headers
// from a downstream CMake project (R34: real API usage, not a stub).
#include <enchantum/enchantum.hpp>
#include <enchantum/iostream.hpp>

#include <iostream>
#include <string_view>

enum class Music { Rock, Jazz, Metal };

int main() {
    // to_string
    const std::string_view name = enchantum::to_string(Music::Rock);
    if (name != "Rock") {
        std::cerr << "FAIL: to_string(Music::Rock) != \"Rock\" (got \""
                  << name << "\")\n";
        return 1;
    }

    // cast (case-sensitive string -> enum)
    const auto jazz = enchantum::cast<Music>("Jazz");
    if (!jazz.has_value() || *jazz != Music::Jazz) {
        std::cerr << "FAIL: cast<Music>(\"Jazz\") failed\n";
        return 1;
    }

    // iteration over values
    int count = 0;
    for (const Music m : enchantum::values_generator<Music>) {
        (void)m;
        ++count;
    }
    if (count != 3) {
        std::cerr << "FAIL: values_generator<Music> yielded " << count
                  << " entries (expected 3)\n";
        return 1;
    }

    // enum <-> index
    const auto idx = enchantum::enum_to_index(Music::Metal);
    if (!idx.has_value() || *idx != 2) {
        std::cerr << "FAIL: enum_to_index(Music::Metal) != 2\n";
        return 1;
    }

    std::cout << "enchantum consumer test: OK\n";
    return 0;
}