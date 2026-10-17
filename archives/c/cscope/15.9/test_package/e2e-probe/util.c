#include "util.h"

int tokenize(const char *src) {
    int n = 0;
    while (src[n] != '\0') {
        n++;
    }
    return n;
}

int checksum(int n) {
    return (n * 31) % 1021;
}
