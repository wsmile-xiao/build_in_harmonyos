#include <hocon/config.hpp>

// for boost::get on config_value::unwrapped() variant
#include <boost/variant.hpp>

// Conan default build_type is Release (CMake adds -DNDEBUG, which strips
// assert() including its compile-time type checks). Keep the 6 functional
// assertions live in every build type (review note 2026-09-10).
#undef NDEBUG
#include <cassert>
#include <iostream>
#include <string>

using namespace hocon;

int main() {
    // Parse + resolve: exercises the tokenizer, parser and substitution
    // resolver (substitutions live in the ${...} form).
    shared_config conf = config::parse_string(R"HOCON(
        root {
            greeting = "Hello"
            name = "HOCON"
            message = ${root.greeting}"-"${root.name}
            port = 8443
            ratio = 0.75
            enabled = true
            list = [1, 2, 3]
        }
    )HOCON")->resolve();

    // Typed reads through the config API.
    assert(conf->get_string("root.message") == "Hello-HOCON");
    assert(conf->get_int("root.port") == 8443);
    assert(conf->get_double("root.ratio") == 0.75);
    assert(conf->get_bool("root.enabled"));
    auto list = conf->get_list("root.list");
    assert(list->size() == 3);
    // config_list has no get_int(size_t); fetch via unwrapped() variant
    // (review note 2026-09-10: the old list->get_int(2) only "compiled"
    // because NDEBUG stripped assert including its operand checks).
    assert(boost::get<int>(list->get(2)->unwrapped()) == 3);

    // Origin/description plumbing (config_origin).
    auto origin = conf->get_value("root.port")->origin();
    assert(origin && !origin->description().empty());

    std::cout << "cpp-hocon test_package OK: parse/resolve/typed-read/"
                 "list/origin all passed" << std::endl;
    return 0;
}
