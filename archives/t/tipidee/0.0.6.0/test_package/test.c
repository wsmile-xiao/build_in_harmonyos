#include <stdio.h>
#include <string.h>
#include <tipidee/tipidee.h>
#include <tipidee/uri.h>
#include <tipidee/method.h>

int main(void) {
    /* Test HTTP method parsing */
    tipidee_method method = tipidee_method_tonum("GET");
    if (method != TIPIDEE_METHOD_GET) {
        fprintf(stderr, "GET method parsing failed\n");
        return 1;
    }

    method = tipidee_method_tonum("POST");
    if (method != TIPIDEE_METHOD_POST) {
        fprintf(stderr, "POST method parsing failed\n");
        return 2;
    }

    /* Test method to string */
    const char *str = tipidee_method_tostr(TIPIDEE_METHOD_GET);
    if (!str || strcmp(str, "GET") != 0) {
        fprintf(stderr, "method tostr failed\n");
        return 3;
    }

    /* Test URI parsing */
    char uri_buf[256];
    tipidee_uri uri = TIPIDEE_URI_ZERO;
    size_t r = tipidee_uri_parse(uri_buf, sizeof(uri_buf), "/path/to/file.html?query=1", &uri);
    if (r == 0) {
        fprintf(stderr, "URI parsing failed\n");
        return 4;
    }

    puts("tipidee API assertions: 4 passed");
    return 0;
}
