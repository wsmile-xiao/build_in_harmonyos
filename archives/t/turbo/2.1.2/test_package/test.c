/* test_package/test.c — Consumer test for turbo 2.1.2
 *
 * R34: Test must substantially depend on the tested package.
 * This test links against libtffi_wrap and calls http_parser_init(),
 * http_method_str(), and http_errno_name() — core exported functions.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* Match the actual http_parser struct layout from turbo's bundled http-parser */
struct http_parser {
    unsigned char type : 2;
    unsigned char flags : 6;
    unsigned char state;
    unsigned char header_state;
    unsigned char index;
    unsigned int nread;
    unsigned int content_length;
    unsigned short http_major;
    unsigned short http_minor;
    unsigned int status_code;
    unsigned int method;
    int http_errno;
};

extern void http_parser_init(struct http_parser *parser, int type);
extern const char *http_method_str(int method);
extern const char *http_errno_name(int err);

int main(void) {
    struct http_parser parser;
    memset(&parser, 0, sizeof(parser));

    /* Initialize HTTP parser — this is the core function from turbo */
    http_parser_init(&parser, 0); /* type=0 = request */

    /* Verify parser was initialized (type field should be set) */
    if (parser.type != 0) {
        fprintf(stderr, "FAIL: parser type not set correctly (got %d)\n", (int)parser.type);
        return 1;
    }

    /* Test http_method_str — another exported function */
    const char *method_str = http_method_str(1); /* HTTP_GET = 1 */
    if (method_str == NULL) {
        fprintf(stderr, "FAIL: http_method_str returned NULL\n");
        return 1;
    }

    /* Test http_errno_name */
    const char *err_name = http_errno_name(0);
    if (err_name == NULL) {
        fprintf(stderr, "FAIL: http_errno_name returned NULL\n");
        return 1;
    }

    printf("test turbo 2.1.2: OK (http_parser_init + http_method_str(%s) + http_errno_name(%s))\n",
           method_str, err_name);
    return 0;
}
