#include <liboath/oath.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    char otp[9] = {0};
    const char *secret = "12345678901234567890";
    if (oath_init() != OATH_OK) return 1;
    if (strcmp(oath_check_version(NULL), OATH_VERSION) != 0) return 2;
    /* RFC 6238 SHA-1 vector: time=59, 8 digits, expected 94287082. */
    if (oath_totp_generate(secret, 20, 59, 30, 0, 8, otp) != OATH_OK)
        return 3;
    if (strcmp(otp, "94287082") != 0) {
        fprintf(stderr, "unexpected TOTP: %s\n", otp);
        return 4;
    }
    oath_done();
    puts("OATH_CONSUMER_PASS");
    return 0;
}
