// test_package consumer test for ctd_cli 0.1.3.
// Simulates an upper-layer business component (consumer) that uses the library
// ONLY through its installed public header korgorusze/CLI.h and public API:
// compile, link, parse real command lines and observe real results.
#include <cstdlib>
#include <iostream>
#include <optional>
#include <string>

#include "korgorusze/CLI.h"

namespace korg = korgorusze;

// The library declares deserialize<T> and expects consumers to provide
// specializations for types they use (upstream unit tests do the same).
template<>
std::optional<std::string> korgorusze::deserialize<std::string>(std::string_view argument) noexcept {
    return std::string{argument};
}

int main() {
    // Subcommand based CLI: named arguments, flags, positional arguments.
    auto cli = korg::Command<"app">{}
            .help("consumer application")
            .subcommandRequired()
            .add(
                    korg::Command<"add">{}
                            .add(korg::Argument<"key">{},
                                 korg::Argument<"value", long int>{})
                            .handler(),
                    korg::Command<"list">{}.handler(),
                    korg::Command<"rm">{}
                            .add(korg::Flag<"all">{}.longFlag<"all">().shortFlag<'a'>())
                            .handler());

    std::string storedKey{};
    long int storedValue = 0;
    bool listCalled = false;

    cli.get<"add">().handler([&](std::string_view key, long int value) {
        storedKey = std::string(key);
        storedValue = value;
        return true;
    });
    cli.get<"list">().handler([&]() {
        listCalled = true;
        return true;
    });
    cli.get<"rm">().handler([&](bool all) {
        if (all) {
            storedKey.clear();
            storedValue = 0;
        }
        return true;
    });

    // 1) Real parse + handler execution.
    if (!cli.parse("add config 42")) {
        std::cerr << "FAIL: parse 'add config 42' should succeed" << std::endl;
        return EXIT_FAILURE;
    }
    if (storedKey != "config" || storedValue != 42) {
        std::cerr << "FAIL: handler did not receive expected values (key='" << storedKey
                  << "' value=" << storedValue << ")" << std::endl;
        return EXIT_FAILURE;
    }

    // 2) Flag parsing (short flag) + handler.
    if (!cli.parse("rm -a")) {
        std::cerr << "FAIL: parse 'rm -a' should succeed" << std::endl;
        return EXIT_FAILURE;
    }
    if (storedKey != "" || storedValue != 0) {
        std::cerr << "FAIL: rm -a handler did not clear state" << std::endl;
        return EXIT_FAILURE;
    }

    // 3) Quoted argument with spaces must be treated as a single argument.
    if (!cli.parse("add \"config file\" 7")) {
        std::cerr << "FAIL: parse quoted argument should succeed" << std::endl;
        return EXIT_FAILURE;
    }
    if (storedKey != "config file" || storedValue != 7) {
        std::cerr << "FAIL: quoted argument parsing broken" << std::endl;
        return EXIT_FAILURE;
    }

    // 4) Error handling: unknown named argument is reported, not silently ignored.
    if (cli.parse("add --nonexistent 1").status() != korg::CliStatusEnum::UnknownArgument) {
        std::cerr << "FAIL: unknown argument must be reported" << std::endl;
        return EXIT_FAILURE;
    }

    std::cout << "test_ctd_cli: consumer OK (subcommand/named/flag/positional/error paths verified)"
              << std::endl;
    return EXIT_SUCCESS;
}
