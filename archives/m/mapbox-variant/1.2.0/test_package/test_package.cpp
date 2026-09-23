#include <mapbox/variant.hpp>

#include <cstdio>
#include <string>

struct length_visitor {
    int operator()(int value) const { return value * 2; }
    int operator()(const std::string& value) const {
        return static_cast<int>(value.size());
    }
};

int main() {
    int failures = 0;
    mapbox::util::variant<int, std::string> value = 21;

    if (!value.is<int>() || mapbox::util::get<int>(value) != 21) {
        std::printf("FAIL basic int access\n");
        ++failures;
    }

    value = std::string("abcd");
    if (!value.is<std::string>() || mapbox::util::get<std::string>(value) != "abcd") {
        std::printf("FAIL string access\n");
        ++failures;
    }

    if (mapbox::util::apply_visitor(length_visitor(), mapbox::util::variant<int, std::string>(21)) != 42 ||
        mapbox::util::apply_visitor(length_visitor(), value) != 4) {
        std::printf("FAIL visitor dispatch\n");
        ++failures;
    }

    if (value.is<int>() || !value.is<std::string>()) {
        std::printf("FAIL type query semantics\n");
        ++failures;
    }

    bool wrong_type_threw = false;
    try {
        (void)mapbox::util::get<int>(value);
    } catch (const mapbox::util::bad_variant_access&) {
        wrong_type_threw = true;
    }
    if (!wrong_type_threw) {
        std::printf("FAIL wrong-type access did not throw\n");
        ++failures;
    }

    if (failures == 0) {
        std::printf("mapbox-variant 1.2.0 consumer: 7 assertions passed\n");
    }
    return failures == 0 ? 0 : 1;
}
