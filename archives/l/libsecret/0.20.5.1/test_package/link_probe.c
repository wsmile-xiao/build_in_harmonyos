/*
 * test_package/link_probe.c — downstream link/run contract probe.
 *
 * This program IS linked against libsecret (`-lsecret-1` via the exported
 * `secret-1` pkg-config module) and uses the public headers, which is exactly
 * what downstream consumers (kylin-keyring, kylin-nm-plugin) do:
 *
 *     #include <libsecret/secret.h>
 *     gcc ... $(pkg-config --cflags --libs libsecret-1)
 *
 * It is executed by the test driver with the produced library copies on
 * LD_LIBRARY_PATH, proving the full link -> load -> call path.
 */
#include <libsecret/secret.h>

#include <stdio.h>
#include <string.h>

int main(void)
{
    SecretValue *value;
    const gchar *text;
    int ok;

    value = secret_value_new("linkprobe", -1, "text/plain");
    if (value == NULL) {
        fprintf(stderr, "FAIL: secret_value_new() returned NULL\n");
        return 1;
    }
    text = secret_value_get(value, NULL);
    ok = (text != NULL && strcmp(text, "linkprobe") == 0);
    secret_value_unref(value);
    if (!ok) {
        fprintf(stderr, "FAIL: -lsecret-1 link probe roundtrip mismatch\n");
        return 1;
    }
    printf("LINK PROBE: -lsecret-1 link + secret_value_* call OK\n");
    return 0;
}
