/* test_package/test.c — heimdal 7.8.0 L1 smoke test
 *
 * Links against libkrb5 (Heimdal) and calls krb5_init_context() to
 * initialize a Kerberos context, verifying the library is usable.
 */
#include <stdio.h>
#include <stdlib.h>
#include <krb5.h>

int main(void) {
    krb5_context context = NULL;
    krb5_error_code ret;

    ret = krb5_init_context(&context);
    if (ret != 0) {
        fprintf(stderr, "FAIL: krb5_init_context returned %d\n", (int)ret);
        return 1;
    }
    if (context == NULL) {
        fprintf(stderr, "FAIL: krb5_init_context returned NULL context\n");
        return 1;
    }
    printf("[ok] krb5_init_context succeeded\n");
    krb5_free_context(context);
    printf("Smoke test PASSED.\n");
    return 0;
}
