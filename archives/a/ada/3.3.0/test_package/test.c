#include <stdio.h>
#include <string.h>
#include "ada_c.h"

int main(void) {
    /* Parse a simple URL using ada's C API */
    const char* input = "https://github.com/ada-url/ada";
    ada_url url = ada_parse(input, strlen(input));
    if (url == NULL) {
        printf("FAIL: ada_parse returned NULL\n");
        return 1;
    }

    ada_string href = ada_get_href(url);
    printf("ada 3.3.0 test: href=%.*s\n", (int)href.length, href.data);

    ada_string host = ada_get_host(url);
    printf("ada 3.3.0 test: host=%.*s\n", (int)host.length, host.data);

    ada_string proto = ada_get_protocol(url);
    printf("ada 3.3.0 test: protocol=%.*s\n", (int)proto.length, proto.data);

    ada_free(url);

    printf("test ada 3.3.0: OK\n");
    return 0;
}
