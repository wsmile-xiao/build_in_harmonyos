/* legacycrypt 0.3 test_package — C consumer (exec-time dependency check).
 *
 * Compiled and run by test_package/conanfile.py test().  It links the
 * libxcrypt shared package (SONAME libcrypt.so.2) as its own DT_NEEDED and
 * exercises the exact functionality legacycrypt.py wraps: a real crypt_r()
 * round-trip.  Exec-time NEEDED loading is the loader path OHOS CI workers
 * accept for freshly built user-directory shared objects, while post-start
 * dlopen() of the same files is refused with EACCES (see notes.md and the
 * numpy 1.26.4 precedent), so this is the worker-reliable half of the
 * acceptance.  On the interactive device both paths run for real.
 */
#include <crypt.h>
#include <stdio.h>
#include <string.h>

/* libxcrypt crypt_data is ~32 KiB — keep it off the stack. */
static struct crypt_data data1;
static struct crypt_data data2;

int main(void)
{
    const char *pass = "mypassword";
    const char *salt = "$6$0123456789abcdef"; /* SHA512, 16 salt chars */
    char *h1, *h2;

    memset(&data1, 0, sizeof(data1));
    memset(&data2, 0, sizeof(data2));
    h1 = crypt_r(pass, salt, &data1);
    if (h1 == NULL || h1[0] == '*') {
        printf("FAIL: crypt_r returned a failure token\n");
        return 1;
    }
    h2 = crypt_r(pass, h1, &data2);
    if (h2 == NULL || strcmp(h2, h1) != 0) {
        printf("FAIL: crypt_r round-trip mismatch\n");
        return 1;
    }
    printf("OK: libcrypt crypt_r round-trip works\n");
    return 0;
}
