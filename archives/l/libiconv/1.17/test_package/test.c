#include <stdio.h>
#include <string.h>
#include <iconv.h>

int main() {
    /* Test: convert "Hello" from UTF-8 to ASCII */
    iconv_t cd = iconv_open("ASCII", "UTF-8");
    if (cd == (iconv_t)-1) {
        fprintf(stderr, "iconv_open failed\n");
        return 1;
    }

    char inbuf[] = "Hello";
    char outbuf[64];
    char *inptr = inbuf;
    char *outptr = outbuf;
    size_t inbytes = strlen(inbuf);
    size_t outbytes = sizeof(outbuf);

    size_t ret = iconv(cd, &inptr, &inbytes, &outptr, &outbytes);
    if (ret == (size_t)-1) {
        fprintf(stderr, "iconv conversion failed\n");
        iconv_close(cd);
        return 1;
    }

    /* Null-terminate the output */
    *outptr = '\0';

    if (strcmp(outbuf, "Hello") != 0) {
        fprintf(stderr, "Conversion mismatch: got '%s'\n", outbuf);
        iconv_close(cd);
        return 1;
    }

    iconv_close(cd);
    printf("libiconv test passed: UTF-8 -> ASCII conversion OK\n");
    return 0;
}
