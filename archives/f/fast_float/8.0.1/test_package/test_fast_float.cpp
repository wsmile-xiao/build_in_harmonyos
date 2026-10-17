/* fast_float test_package consumer probe.
 * Parses a float string with fast_float::from_chars and verifies the value.
 */
#include <fast_float/fast_float.h>
#include <cstdio>
#include <cstring>

int main(void)
{
    const char *s = "3.14159265";
    double value = 0.0;
    auto answer = fast_float::from_chars(s, s + strlen(s), value);
    if (answer.ec != std::errc() || value < 3.14 || value > 3.15) {
        std::fprintf(stderr, "FAIL: from_chars parse error\n");
        return 1;
    }
    std::printf("fast_float OK (parsed %.8f)\n", value);
    return 0;
}
