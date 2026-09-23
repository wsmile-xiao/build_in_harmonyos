#include <stdio.h>
#include <string.h>

#include <sasl/sasl.h>

static int check(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    printf("ok: %s\n", message);
    return 0;
}

int main(void)
{
    int failures = 0;

    const char *implementation = NULL;
    const char *version = NULL;
    int major = 0;
    int minor = 0;
    int step = 0;
    int patch = 0;

    sasl_version_info(&implementation, &version, &major, &minor, &step, &patch);
    failures += check(implementation != NULL, "implementation string is available");
    failures += check(major == 2 && minor == 1, "major/minor version is 2.1");

    int result = sasl_client_init(NULL);
    failures += check(result == SASL_OK, "sasl_client_init succeeds");
    if (result != SASL_OK) {
        return 1;
    }

    sasl_conn_t *client = NULL;
    result = sasl_client_new("imap", "localhost", NULL, NULL, NULL, 0, &client);
    failures += check(result == SASL_OK && client != NULL, "sasl_client_new creates a connection");

    if (client != NULL) {
        sasl_dispose(&client);
    }
    sasl_done();

    if (failures != 0) {
        return 1;
    }

    printf("libsasl consumer checks passed: %s %s\n",
        implementation != NULL ? implementation : "(null)",
        version != NULL ? version : "(null)");
    return 0;
}
