#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "cbf.h"

/*
 * Real consumer of the packaged libcbf: builds a small CBF data set through
 * the public API (handle + datablock/category/column/rows), writes it as a
 * real binary CBF file, reads the file back and verifies the text value and
 * the packed binary array survive the round trip element-by-element.
 *
 * Exercises: cbf_make_handle, cbf_free_handle, cbf_new_datablock,
 * cbf_new_category, cbf_new_column, cbf_set_value,
 * cbf_set_integerarray_wdims, cbf_write_file, cbf_read_file,
 * cbf_find_datablock/category/column, cbf_count_rows, cbf_select_row,
 * cbf_get_value, cbf_get_integerarrayparameters_wdims, cbf_get_integerarray.
 */

#define W 8
#define H 6

static int fails = 0;

static int fail(const char *what, int err, int line)
{
    fprintf(stderr, "FAIL at line %d: %s -> cbf error %d\n", line, what, err);
    fails++;
    return 1;
}

int main(void)
{
    const char *path = "consumer_roundtrip.cbf";
    cbf_handle h = NULL;
    int data[W * H];
    unsigned int i;
    int err;

    for (i = 0; i < (unsigned)(W * H); i++)
        data[i] = (int)(i * 7 % 251);

    /* 1. build a datablock with a text row and a 2-D packed binary array */
    if ((err = cbf_make_handle(&h))) return fail("cbf_make_handle", err, __LINE__);
    if ((err = cbf_new_datablock(h, "consumer"))) return fail("new_datablock", err, __LINE__);
    if ((err = cbf_new_category(h, "meta"))) return fail("new_category", err, __LINE__);
    if ((err = cbf_new_column(h, "tag"))) return fail("new_column", err, __LINE__);
    if ((err = cbf_set_value(h, "hello-cbflib-on-ohos"))) return fail("set_value", err, __LINE__);
    if ((err = cbf_new_category(h, "array_data"))) return fail("new_category", err, __LINE__);
    if ((err = cbf_new_column(h, "data"))) return fail("new_column", err, __LINE__);
    if ((err = cbf_set_integerarray_wdims(h, CBF_PACKED, 1, data, sizeof(int), 1,
                                          (size_t)(W * H), "little_endian",
                                          W, H, 1, 0)))
        return fail("set_integerarray_wdims", err, __LINE__);

    /* 2. write it as a real binary CBF file */
    {
        FILE *out = fopen(path, "w+b");
        if (!out) { perror("fopen out"); return 1; }
        err = cbf_write_file(h, out, 0, CBF, MSG_NODIGEST, ENC_DEFAULT);
        if (err) { fclose(out); return fail("cbf_write_file", err, __LINE__); }
        fclose(out);
    }
    cbf_free_handle(h);
    h = NULL;

    /* 3. read the file back and verify contents.
     * The handle references the input stream until the binary values are
     * fetched, so the FILE* must stay open until step 3 is done. */
    if ((err = cbf_make_handle(&h))) return fail("cbf_make_handle 2", err, __LINE__);
    FILE *in = fopen(path, "rb");
    if (!in) { perror("fopen in"); return 1; }
    err = cbf_read_file(h, in, MSG_DIGEST);
    if (err) { fclose(in); return fail("cbf_read_file", err, __LINE__); }
    if ((err = cbf_find_datablock(h, "consumer"))) return fail("find_datablock", err, __LINE__);
    if ((err = cbf_find_category(h, "meta"))) return fail("find_category", err, __LINE__);
    if ((err = cbf_find_column(h, "tag"))) return fail("find_column", err, __LINE__);
    {
        unsigned int rows = 0;
        const char *value = NULL;
        if ((err = cbf_count_rows(h, &rows))) return fail("count_rows", err, __LINE__);
        if (rows != 1) { fprintf(stderr, "FAIL: rows=%u != 1\n", rows); return 1; }
        if ((err = cbf_select_row(h, 0))) return fail("select_row", err, __LINE__);
        if ((err = cbf_get_value(h, &value))) return fail("get_value", err, __LINE__);
        if (!value || strcmp(value, "hello-cbflib-on-ohos") != 0) {
            fprintf(stderr, "FAIL: round-trip text mismatch: %s\n", value ? value : "(null)");
            return 1;
        }
    }
    if ((err = cbf_find_category(h, "array_data"))) return fail("find_category 2", err, __LINE__);
    if ((err = cbf_find_column(h, "data"))) return fail("find_column 2", err, __LINE__);
    if ((err = cbf_select_row(h, 0))) return fail("select_row 2", err, __LINE__);
    {
        int back[W * H];
        unsigned int compression = 0;
        int id = 0, elsigned = 0, elunsigned = 0, minelem = 0, maxelem = 0;
        size_t elsize = 0, nelem = 0, elements_read = 0;
        size_t dimfast = 0, dimmid = 0, dimslow = 0, padding = 0;
        const char *byteorder = NULL;
        err = cbf_get_integerarrayparameters_wdims(
            h, &compression, &id, &elsize, &elsigned, &elunsigned, &nelem,
            &minelem, &maxelem, &byteorder, &dimfast, &dimmid, &dimslow, &padding);
        if (err) return fail("get_integerarrayparameters_wdims", err, __LINE__);
        if (nelem != (size_t)(W * H)) {
            fprintf(stderr, "FAIL: element count %lu != %d\n",
                    (unsigned long)nelem, W * H);
            return 1;
        }
        if (dimfast != W || dimmid != H || dimslow != 1) {
            fprintf(stderr, "FAIL: dims %lux%lux%lu != %dx%dx1\n",
                    (unsigned long)dimfast, (unsigned long)dimmid,
                    (unsigned long)dimslow, W, H);
            return 1;
        }
        err = cbf_get_integerarray(h, &id, back, sizeof(int), 1, nelem, &elements_read);
        if (err) return fail("get_integerarray", err, __LINE__);
        if (elements_read != nelem) {
            fprintf(stderr, "FAIL: read %lu of %lu elements\n",
                    (unsigned long)elements_read, (unsigned long)nelem);
            return 1;
        }
        for (i = 0; i < (unsigned)nelem; i++) {
            if (back[i] != data[i]) {
                fprintf(stderr, "FAIL: element %u: got %d expected %d\n",
                        i, back[i], data[i]);
                return 1;
            }
        }
    }
    cbf_free_handle(h);
    fclose(in);
    remove(path);

    if (fails) return 1;
    printf("cbflib consumer round-trip OK: text value + %dx%d packed int array verified\n",
           W, H);
    return 0;
}
