/* Consumer test for purelibc 1.0.8 on OHOS (fopen mode parsing).
 *
 * _pure_parse_mode() is the exported helper purelibc uses to map fopen
 * mode strings onto open(2) flags. The test asserts the real mappings
 * against the host <fcntl.h> constants, so a mismatch in the library's
 * mode handling fails loudly instead of corrupting file semantics. */
#include <fcntl.h>
#include <purelibc.h>

int main(void)
{
    if (_pure_parse_mode("r") != O_RDONLY)
        return 1;
    if (_pure_parse_mode("w") != (O_WRONLY | O_CREAT | O_TRUNC))
        return 2;
    if (_pure_parse_mode("a") != (O_WRONLY | O_CREAT | O_APPEND))
        return 3;
    if (_pure_parse_mode("r+") != O_RDWR)
        return 4;
    if (_pure_parse_mode("w+") != (O_RDWR | O_CREAT | O_TRUNC))
        return 5;
    if (_pure_parse_mode("rb") != O_RDONLY)
        return 6;
    return 0;
}
