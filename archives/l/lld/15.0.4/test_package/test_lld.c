#include <stdio.h>

int main(void) {
    if (puts("linked by lld") == EOF) {
        return 1;
    }
    return 0;
}
