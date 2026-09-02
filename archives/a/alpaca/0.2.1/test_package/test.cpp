#include <cstdlib>
#include <cstdint>
#include <chrono>
#include <system_error>
#include <vector>

#include <alpaca/alpaca.h>

struct Config {
    int id;
    double ratio;
    std::chrono::milliseconds timeout;
    std::vector<bool> flags;
};

int main() {
    Config input{42, 3.5, std::chrono::milliseconds{500}, {true, false, true}};
    std::vector<std::uint8_t> bytes;
    const auto written = alpaca::serialize(input, bytes);
    std::error_code error;
    const auto output = alpaca::deserialize<Config>(bytes, error);
    if (error || written == 0 || output.id != input.id ||
        output.ratio != input.ratio || output.timeout != input.timeout ||
        output.flags != input.flags) {
        return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
