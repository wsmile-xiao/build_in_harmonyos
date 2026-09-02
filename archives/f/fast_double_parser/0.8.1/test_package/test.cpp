#include <cmath>
#include <cstdlib>

#include <fast_double_parser.h>

int main() {
    double value = 0.0;
    const char input[] = "-123.456e2";
    const char *end = fast_double_parser::parse_number(input, &value);
    if (end != input + sizeof(input) - 1 || std::fabs(value + 12345.6) > 1e-9) {
        return EXIT_FAILURE;
    }
    return EXIT_SUCCESS;
}
