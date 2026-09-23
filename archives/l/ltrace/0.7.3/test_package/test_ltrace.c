/* Test program for ltrace
 * This program will be traced by ltrace to verify it works correctly.
 */
#include <stdio.h>
#include <string.h>

int main() {
    /* Call some library functions that ltrace can trace */
    const char *msg = "Hello from ltrace test";
    size_t len = strlen(msg);
    printf("Message length: %zu\n", len);
    return 0;
}
