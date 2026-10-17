#include <nonstd/variant.hpp>

#include <cmath>
#include <iostream>
#include <string>
#include <type_traits>

int main() {
    nonstd::variant<int, double, std::string> value = 42;
    if (nonstd::get<int>(value) != 42) return 1;
    if (value.index() != 0) return 2;

    value = std::string("hello");
    if (!nonstd::holds_alternative<std::string>(value)) return 3;
    if (nonstd::get<std::string>(value) != "hello") return 4;

    if (nonstd::get_if<double>(&value) != nullptr) return 5;
    const int length = nonstd::visit(
        [](const auto& item) -> int {
            using T = std::decay_t<decltype(item)>;
            if constexpr (std::is_same<T, std::string>::value) {
                return static_cast<int>(item.size());
            } else {
                return static_cast<int>(item);
            }
        }, value);
    if (length != 5) return 6;

    value = 3.14;
    if (std::fabs(nonstd::get<double>(value) - 3.14) > 0.01) return 7;
    if (value.index() != 1) return 8;

    std::cout << "PASS: variant-lite core API consumer test" << std::endl;
    return 0;
}
