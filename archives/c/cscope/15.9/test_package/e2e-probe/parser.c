#include "parser.h"
#include "util.h"

int parse_input(const char *src) {
    int n = tokenize(src);
    return checksum(n);
}

int parse_twice(const char *src) {
    return parse_input(src) + parse_input(src);
}
