#include <krb5.h>
#include <stdio.h>
#include <string.h>

int main(void) {
    krb5_context ctx;
    krb5_error_code ret;

    ret = krb5_init_context(&ctx);
    if (ret) {
        fprintf(stderr, "krb5_init_context failed: %d\n", ret);
        return 1;
    }
    printf("krb5_init_context: OK\n");

    /* Verify we can get the default realm */
    char *realm = NULL;
    ret = krb5_get_default_realm(ctx, &realm);
    if (ret == 0 && realm) {
        printf("krb5_get_default_realm: %s\n", realm);
        krb5_free_default_realm(ctx, realm);
    } else {
        printf("krb5_get_default_realm: (not configured, expected on test env)\n");
    }

    krb5_free_context(ctx);
    printf("krb5_free_context: OK\n");
    printf("All krb5 tests passed!\n");
    return 0;
}
