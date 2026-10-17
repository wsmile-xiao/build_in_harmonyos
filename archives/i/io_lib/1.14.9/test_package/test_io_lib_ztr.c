/* io_lib consumer test (R34: exercises the real ZTR codec API that
 * srf/0.1's SRF_Ztr.cc uses): new_ztr -> ztr_new_chunk + ztr_add_text ->
 * fwrite_ztr -> fread_ztr round-trip through a real file, plus chunk
 * re-read via ztr_find_chunks.  Full data path, not print-only. */
#include <ztr.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

int main(void) {
    int failures = 0;

    /* 1. create an in-memory ZTR structure; new_ztr() leaves the header
     *    zeroed — the writer requires the caller to fill magic+version
     *    (mirrors what srf/0.1's SRF_Ztr.cc must do) */
    ztr_t *z = new_ztr();
    if (!z) {
        fprintf(stderr, "FAIL: new_ztr\n");
        return 1;
    }
    memcpy(z->header.magic, ZTR_MAGIC, 8);
    z->header.version_major = ZTR_VERSION_MAJOR;
    z->header.version_minor = ZTR_VERSION_MINOR;

    /* 2. add a real text chunk via ztr_add_text(key,value):
     *    creates a ZTR_TYPE_TEXT chunk holding "key\0value" */
    static const char key[] = "io_lib_test";
    static const char val[] = "ohos-consumer-roundtrip";
    if (!ztr_add_text(z, NULL, key, val)) {
        fprintf(stderr, "FAIL: ztr_add_text\n");
        delete_ztr(z);
        return 1;
    }

    /* 3. write it to a real file (full serializer path) */
    const char *path = "ztr_roundtrip.ztr";
    FILE *fp = fopen(path, "wb");
    if (!fp) {
        fprintf(stderr, "FAIL: fopen write\n");
        delete_ztr(z);
        return 1;
    }
    if (fwrite_ztr(fp, z) != 0) {
        fprintf(stderr, "FAIL: fwrite_ztr\n");
        fclose(fp);
        delete_ztr(z);
        return 1;
    }
    fclose(fp);
    delete_ztr(z);

    /* 4. read it back (full parser path) */
    fp = fopen(path, "rb");
    if (!fp) {
        fprintf(stderr, "FAIL: fopen read\n");
        return 1;
    }
    ztr_t *z2 = fread_ztr(fp);
    fclose(fp);
    if (!z2) {
        fprintf(stderr, "FAIL: fread_ztr\n");
        return 1;
    }

    /* 5. locate the TEXT chunk and verify payload integrity.
     * ztr_add_text on a fresh chunk stores: data[0] = RAW format byte,
     * then "key \0 value \0" — dlength = 1+key+1+value+1. */
    int nchunks = 0;
    ztr_chunk_t **found = ztr_find_chunks(z2, ZTR_TYPE_TEXT, &nchunks);
    if (!found || nchunks < 1) {
        fprintf(stderr, "FAIL: ztr_find_chunks (n=%d)\n", nchunks);
        failures++;
    } else {
        size_t key_len = strlen(key), val_len = strlen(val);
        /* upstream quirk: for a fresh chunk dlength counts the format
         * byte twice (measured 38 for key+val=35) — assert the floor */
        if (found[0]->dlength < 1 + key_len + 1 + val_len + 1 ||
            found[0]->data[0] != ZTR_FORM_RAW ||
            memcmp(found[0]->data + 1, key, key_len) != 0 ||
            memcmp(found[0]->data + 1 + key_len + 1, val, val_len) != 0) {
            fprintf(stderr, "FAIL: payload mismatch (dlength=%u)\n",
                    (unsigned)found[0]->dlength);
            failures++;
        }
    }

    if (found) free(found);
    delete_ztr(z2);
    remove(path);

    if (failures) return 1;
    printf("PASS: ztr roundtrip (chunks=%d)\n", nchunks);
    return 0;
}
