#include <stddef.h>
#include <stdio.h>
#include <string.h>

#include "picohttpparser.h"

int main(void) {
    const char request[] = "GET / HTTP/1.1\r\nHost: example.com\r\n\r\n";
    const char *method;
    const char *path;
    int minor_version;
    struct phr_header headers[4];
    size_t method_len, path_len, num_headers = 4;
    int consumed = phr_parse_request(request, strlen(request), &method, &method_len,
                                     &path, &path_len, &minor_version, headers,
                                     &num_headers, 0);
    if (consumed <= 0 || method_len != 3 || strncmp(method, "GET", method_len) != 0 ||
        path_len != 1 || path[0] != '/' || minor_version != 1 || num_headers != 1) {
        return 1;
    }
    puts("picohttpparser API test passed");
    return 0;
}
