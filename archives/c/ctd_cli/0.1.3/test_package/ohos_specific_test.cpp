// HarmonyOS-specific test for ctd_cli 0.1.3.
// Exercises behaviors relevant to HarmonyOS PC apps through the public API:
//   - UTF-8 (Chinese) strings in command lines (common in OHOS UI/CLI apps),
//   - argv-style long/short flags and missing-value error reporting.
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
    // CLI used by an OHOS-style application: configures a device over command line.
    std::string name{};
    bool verbose = false;
    std::optional<int> count{};

    auto cli = korg::Command<"ohos-tool">{}
            .add(
                    korg::Argument<"name", std::string>{}.longFlag<"name">().shortFlag<'n'>().set(name),
                    korg::Flag<"verbose">{}.longFlag<"verbose">().shortFlag<'v'>().set(verbose),
                    korg::Argument<"count", int>{}.optional().set(count));

    // 1) Chinese UTF-8 argument values must round-trip intact.
    if (!cli.parse("--name 设备A -v")) {
        std::cerr << "FAIL: parse with Chinese UTF-8 value should succeed" << std::endl;
        return EXIT_FAILURE;
    }
    if (name != "设备A" || !verbose) {
        std::cerr << "FAIL: UTF-8 value or flag state lost (name='" << name
                  << "' verbose=" << verbose << ")" << std::endl;
        return EXIT_FAILURE;
    }

    // 2) Short flag + optional positional via argv style.
    count.reset();
    if (!cli.parse("-n hub -v 3")) {
        std::cerr << "FAIL: short flag parse should succeed" << std::endl;
        return EXIT_FAILURE;
    }
    if (name != "hub" || !verbose || !count.has_value() || *count != 3) {
        std::cerr << "FAIL: short flag/positional values incorrect" << std::endl;
        return EXIT_FAILURE;
    }

    // 3) Missing mandatory argument must be reported with the exact error enum.
    if (cli.parse("--verbose").status() != korg::CliStatusEnum::MissingArgument) {
        std::cerr << "FAIL: missing mandatory argument must be reported" << std::endl;
        return EXIT_FAILURE;
    }

    // 4) Empty input must not crash and must be a graceful no-op.
    cli.parse("");

    std::cout << "test_ohos_specific: OK (UTF-8 / flags / missing-arg / empty input)" << std::endl;
    return EXIT_SUCCESS;
}