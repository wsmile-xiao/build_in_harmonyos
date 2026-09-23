#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <libcitadel.h>

int main(void)
{
    StrBuf *buf = NewStrBuf();
    if (buf == NULL) {
        printf("LIBCITADEL_TEST strbuf_new FAIL\n");
        return 1;
    }
    /* StrBufPlain returns the new length (CopySize), not 0.
     * Upstream lib/stringbuf.c: `return CopySize;` (-1 only on error). */
    if (StrBufPlain(buf, "citadel", 7) != 7) {
        printf("LIBCITADEL_TEST strbuf_plain FAIL\n");
        FreeStrBuf(&buf);
        return 2;
    }
    if (StrLength(buf) != 7) {
        printf("LIBCITADEL_TEST strbuf_length FAIL\n");
        FreeStrBuf(&buf);
        return 3;
    }
    if (ChrPtr(buf) == NULL || strcmp(ChrPtr(buf), "citadel") != 0) {
        printf("LIBCITADEL_TEST strbuf_content FAIL\n");
        FreeStrBuf(&buf);
        return 4;
    }
    StrBufAppendPrintf(buf, "-%s", "917");
    if (StrLength(buf) != 11 || strcmp(ChrPtr(buf), "citadel-917") != 0) {
        printf("LIBCITADEL_TEST strbuf_append FAIL\n");
        FreeStrBuf(&buf);
        return 5;
    }
    printf("LIBCITADEL_TEST strbuf_contract PASS\n");
    FreeStrBuf(&buf);

    /* String keys need the generic hashlittle (NULL algorithm).
     * Flathash only accepts sizeof(int) keys (upstream lib/hash.c returns 0
     * otherwise), so it must not be used for "citadel"/7 here. */
    HashList *hash = NewHash(1, NULL);
    if (hash == NULL) {
        printf("LIBCITADEL_TEST hash_new FAIL\n");
        return 6;
    }
    /* Heap payload: Put with NULL destructor takes ownership via free(),
     * so a stack address must not be stored (would corrupt the heap on
     * DeleteHash). */
    int *marker = (int *)malloc(sizeof(int));
    if (marker == NULL) {
        printf("LIBCITADEL_TEST hash_new FAIL\n");
        DeleteHash(&hash);
        return 6;
    }
    *marker = 42;
    Put(hash, "citadel", 7, marker, NULL);
    void *found = NULL;
    if (GetHash(hash, "citadel", 7, &found) == 0 || found != marker) {
        printf("LIBCITADEL_TEST hash_roundtrip FAIL\n");
        DeleteHash(&hash);
        return 7;
    }
    if (TestValidateHash(hash) != 0) {
        printf("LIBCITADEL_TEST hash_validate FAIL\n");
        DeleteHash(&hash);
        return 8;
    }
    printf("LIBCITADEL_TEST hash_contract PASS\n");
    DeleteHash(&hash);

    printf("LIBCITADEL_TEST all PASS\n");
    return 0;
}
