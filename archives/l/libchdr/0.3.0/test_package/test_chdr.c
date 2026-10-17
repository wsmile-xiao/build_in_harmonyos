#include <stdio.h>
#include <string.h>

#include <libchdr/chd.h>

static const char *missing_path(const char *fallback)
{
    return fallback;
}

int main(int argc, char **argv)
{
    int fault_injection = (argc > 1 && strcmp(argv[1], "--missing-path") == 0);
    /* Fixed nonexistent fixture name: the file must NOT exist, so a
       graceful error (not success, not crash) is the only pass. */
    const char *no_such = missing_path("hmbs-nonexistent-fixture-0-3-0.chd");
    int checks = 0;
    chd_file *chd = NULL;
    chd_error err;

    /* 1. Error-string API returns a usable message. */
    {
        const char *msg = chd_error_string(CHDERR_NONE);
        if (msg == NULL || msg[0] == '\0') {
            printf("FAIL: chd_error_string(CHDERR_NONE) empty\n");
            return 1;
        }
        printf("chd_error_string(CHDERR_NONE) = \"%s\"\n", msg);
        checks++;
    }

    /* 2. On-disk header size constants match the spec. */
    if (CHD_V5_HEADER_SIZE != 124 || CHD_MAX_HEADER_SIZE != CHD_V5_HEADER_SIZE) {
        printf("FAIL: header size constants unexpected (%d/%d)\n",
               (int)CHD_V5_HEADER_SIZE, (int)CHD_MAX_HEADER_SIZE);
        return 1;
    }
    printf("header constants ok: V5=%d MAX=%d\n",
           (int)CHD_V5_HEADER_SIZE, (int)CHD_MAX_HEADER_SIZE);
    checks++;

    /* 3. chd_open() on a missing file must fail gracefully. */
    err = chd_open(no_such, CHD_OPEN_READ, NULL, &chd);
    if (err == CHDERR_NONE) {
        if (chd != NULL) {
            chd_close(chd);
        }
        printf("FAIL: chd_open unexpectedly succeeded on missing file\n");
        return 1;
    }
    printf("chd_open(missing) -> %s\n", chd_error_string(err));
    checks++;

    /* 4. chd_read_header() on a missing file must fail gracefully. */
    {
        chd_header header;
        memset(&header, 0, sizeof(header));
        err = chd_read_header(no_such, &header);
        if (err == CHDERR_NONE) {
            printf("FAIL: chd_read_header unexpectedly succeeded on missing file\n");
            return 1;
        }
        printf("chd_read_header(missing) -> %s\n", chd_error_string(err));
        checks++;
    }

    /* 5. Error strings are non-empty across representative codes. */
    {
        static const chd_error codes[] = {
            CHDERR_INVALID_FILE, CHDERR_INVALID_PARAMETER,
            CHDERR_FILE_NOT_FOUND, CHDERR_DECOMPRESSION_ERROR
        };
        size_t i;
        for (i = 0; i < sizeof(codes) / sizeof(codes[0]); i++) {
            const char *msg = chd_error_string(codes[i]);
            if (msg == NULL || msg[0] == '\0') {
                printf("FAIL: chd_error_string(%d) empty\n", (int)codes[i]);
                return 1;
            }
        }
        printf("error strings ok for %u codes\n",
               (unsigned)(sizeof(codes) / sizeof(codes[0])));
        checks++;
    }

    /* 6. Fault-injection scenario re-verifies rejection of a missing path. */
    if (fault_injection) {
        chd_file *probe = NULL;
        err = chd_open("hmbs-fault-injection-missing.chd", CHD_OPEN_READ, NULL, &probe);
        if (err == CHDERR_NONE) {
            if (probe != NULL) {
                chd_close(probe);
            }
            printf("FAIL: fault-injection open unexpectedly succeeded\n");
            return 1;
        }
        printf("fault-injection open rejected -> %s\n", chd_error_string(err));
        checks++;
        printf("test_chdr: fault-injection passed (%d checks)\n", checks);
    } else {
        printf("test_chdr: normal scenario passed (%d checks)\n", checks);
    }
    return 0;
}
