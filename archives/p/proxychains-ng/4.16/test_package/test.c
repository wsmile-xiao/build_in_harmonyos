#include <stdio.h>
#include <stdint.h>

/* dalias_hash is an exported function from libproxychains4.so
 * It computes a hash of the input string.
 * We call it to verify the library is properly linked and functional.
 */
extern uint32_t dalias_hash(char *s0);

int main(void) {
    char *test_str = "proxychains-ng-test";
    uint32_t h = dalias_hash(test_str);
    if (h == 0) {
        printf("FAIL: dalias_hash returned 0 for non-empty input\n");
        return 1;
    }
    printf("test proxychains-ng 4.16: dalias_hash(\"%s\") = %u — OK\n", test_str, h);
    return 0;
}
