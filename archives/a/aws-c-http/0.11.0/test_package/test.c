#include <aws/http/http.h>
#include <aws/http/status_code.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    /* Verify API: aws_http_status_text returns correct string for HTTP 200 */
    const char *ok_text = aws_http_status_text(AWS_HTTP_STATUS_CODE_200_OK);
    if (ok_text == NULL || strcmp(ok_text, "OK") != 0) {
        fprintf(stderr, "FAIL: aws_http_status_text(200) returned '%s', expected 'OK'\n",
                ok_text ? ok_text : "(null)");
        return 1;
    }

    /* Verify API: aws_http_method_get is a valid byte cursor */
    struct aws_byte_cursor method_get = aws_http_method_get;
    if (method_get.len == 0 || method_get.ptr == NULL) {
        fprintf(stderr, "FAIL: aws_http_method_get is empty\n");
        return 1;
    }

    /* Verify method_get cursor contains "GET" */
    if (method_get.len != 3 || strncmp((const char *)method_get.ptr, "GET", 3) != 0) {
        fprintf(stderr, "FAIL: aws_http_method_get is not 'GET'\n");
        return 1;
    }

    printf("test aws-c-http 0.11.0: OK\n");
    return 0;
}
