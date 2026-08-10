#include <olm/olm.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    uint8_t major, minor, patch;
    olm_get_library_version(&major, &minor, &patch);
    printf("olm version: %d.%d.%d\n", major, minor, patch);

    if (major != 3 || minor != 2 || patch != 16) {
        printf("FAIL: unexpected version\n");
        return 1;
    }

    /* Allocate account */
    size_t acct_size = olm_account_size();
    void *acct_buf = malloc(acct_size);
    if (!acct_buf) {
        printf("FAIL: malloc account\n");
        return 1;
    }
    OlmAccount *account = olm_account(acct_buf);
    if (!account) {
        printf("FAIL: olm_account()\n");
        free(acct_buf);
        return 1;
    }

    /* Create account with random bytes */
    size_t rnd_len = olm_create_account_random_length(account);
    void *rnd_buf = malloc(rnd_len);
    if (!rnd_buf) {
        printf("FAIL: malloc random\n");
        free(acct_buf);
        return 1;
    }

    /* Fill with pseudo-random data from /dev/urandom */
    FILE *f = fopen("/dev/urandom", "r");
    if (!f) {
        /* Fallback: use zeroes for test */
        memset(rnd_buf, 0x42, rnd_len);
    } else {
        size_t nread = fread(rnd_buf, 1, rnd_len, f);
        fclose(f);
        if (nread != rnd_len) {
            memset(rnd_buf, 0x42, rnd_len);
        }
    }

    size_t result = olm_create_account(account, rnd_buf, rnd_len);
    if (result == olm_error()) {
        printf("FAIL: olm_create_account: %s\n", olm_account_last_error(account));
        free(rnd_buf);
        free(acct_buf);
        return 1;
    }

    /* Get identity keys */
    size_t keys_len = olm_account_identity_keys_length(account);
    char *keys = malloc(keys_len + 1);
    if (!keys) {
        printf("FAIL: malloc keys\n");
        free(rnd_buf);
        free(acct_buf);
        return 1;
    }

    size_t written = olm_account_identity_keys(account, keys, keys_len);
    if (written == olm_error()) {
        printf("FAIL: olm_account_identity_keys: %s\n", olm_account_last_error(account));
        free(keys);
        free(rnd_buf);
        free(acct_buf);
        return 1;
    }
    keys[written] = '\0';

    printf("identity keys: %s\n", keys);

    free(keys);
    free(rnd_buf);
    free(acct_buf);

    printf("test olm 3.2.16: PASS\n");
    return 0;
}
