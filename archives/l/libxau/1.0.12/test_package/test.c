/* libXau 1.0.12 consumer test — substantive API exercise.
 *
 * Covers:
 *   1. XauFileName()  — resolves the Xauthority path (may be NULL headless).
 *   2. XauWriteAuth() + XauReadAuth() round-trip on a regular file in the
 *      current working directory, verifying every field survives
 *      serialisation. (tmpfile() is NOT usable on OHOS: /tmp is read-only
 *      and musl tmpfile() ignores TMPDIR — see notes.md. Upstream Autest
 *      trivially passes because its final `return (state = 1) ? 0 : 1;`
 *      always returns 0 even when tmpfile() fails.)
 *   3. XauDisposeAuth(NULL) — documented safe no-op.
 *   4. sizeof(Xauth) >= 32 — ABI sanity check (X.Org stable struct layout).
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <X11/Xauth.h>

#define AUTH_FILE "xau-test-auth.bin"

int main(void) {
    int rc = 0;

    /* 1. XauFileName() */
    char *path = XauFileName();
    if (path == NULL) {
        fprintf(stderr, "XauFileName() returned NULL (no Xauthority path)\n");
    } else if (path[0] == '\0') {
        fprintf(stderr, "XauFileName() returned empty string\n");
        rc = 1;
    } else {
        printf("XauFileName() = %s\n", path);
    }

    /* 2. XauWriteAuth -> XauReadAuth round-trip on a CWD file. */
    {
        Xauth orig;
        char name[] = "XAU-TEST-CONAN";
        char data[] = "Do not begin the test until instructed to do so.";
        char empty[] = "";

        memset(&orig, 0, sizeof(orig));
        orig.family = FamilyLocal;
        orig.address_length = 0;
        orig.address = empty;
        orig.number_length = 0;
        orig.number = empty;
        orig.name_length = (unsigned short)strlen(name);
        orig.name = name;
        orig.data_length = (unsigned short)strlen(data);
        orig.data = data;

        FILE *output = fopen(AUTH_FILE, "w+b");
        if (!output) {
            perror("fopen(" AUTH_FILE ")");
            return 2;
        }
        if (XauWriteAuth(output, &orig) == 0) {
            fprintf(stderr, "XauWriteAuth failed\n");
            fclose(output);
            remove(AUTH_FILE);
            return 3;
        }
        rewind(output);

        Xauth *read_back = XauReadAuth(output);
        if (!read_back) {
            fprintf(stderr, "XauReadAuth returned NULL\n");
            fclose(output);
            remove(AUTH_FILE);
            return 4;
        }
        if (read_back->family != orig.family ||
            read_back->address_length != orig.address_length ||
            read_back->number_length != orig.number_length ||
            read_back->name_length != orig.name_length ||
            read_back->data_length != orig.data_length ||
            memcmp(read_back->name, orig.name, orig.name_length) != 0 ||
            memcmp(read_back->data, orig.data, orig.data_length) != 0) {
            fprintf(stderr, "round-trip mismatch (family=%u/%u name='%.*s'/'%.*s')\n",
                    read_back->family, orig.family,
                    (int)read_back->name_length, read_back->name,
                    (int)orig.name_length, orig.name);
            XauDisposeAuth(read_back);
            fclose(output);
            remove(AUTH_FILE);
            return 5;
        }
        XauDisposeAuth(read_back);
        fclose(output);
        remove(AUTH_FILE);
        printf("XauWriteAuth/XauReadAuth round-trip: OK\n");
    }

    /* 3. XauDisposeAuth(NULL) must be a safe no-op. */
    XauDisposeAuth(NULL);

    /* 4. ABI sanity: Xauth struct width. */
    if (sizeof(Xauth) < 32) {
        fprintf(stderr, "sizeof(Xauth) too small: %zu\n", sizeof(Xauth));
        return 6;
    }

    if (rc == 0)
        printf("libXau consumer API test: OK\n");
    return rc;
}
