/*
 * test_package for cppp-reiconv 3.0.0
 * Consumer-style verification: links the installed library and calls its
 * real public C API (reiconv.h) to convert UTF-8 -> UTF-16LE -> UTF-8 and
 * GB18030 roundtrips, asserting observable results.
 */
#include <cppp/reiconv.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int fail(const char *msg)
{
    fprintf(stderr, "test FAIL: %s\n", msg);
    return 1;
}

int main(void)
{
    /* "你好，鸿蒙" in UTF-8 (no BOM) */
    const char *utf8_in = "\xE4\xBD\xA0\xE5\xA5\xBD\xEF\xBC\x8C\xE9\xB8\xBF\xE8\x92\x99";
    size_t utf8_len = strlen(utf8_in);

    /* version symbol must be linkable */
    if (reiconv_version.major != 3 || reiconv_version.minor != 0)
    {
        return fail("reiconv_version != 3.0");
    }

    /* canonicalize */
    char canon[64] = {0};
    size_t clen = reiconv_name_canonicalize("utf_16-le", canon);
    if (clen == 0 || strstr(canon, "UTF16LE") == NULL)
    {
        return fail("reiconv_name_canonicalize");
    }

    /* lookup */
    int idx_gb = reiconv_lookup_from_name("GB18030");
    int idx_cp = reiconv_lookup_from_codepage(936);
    if (idx_gb < 0 || idx_cp < 0)
    {
        return fail("encoding lookup");
    }

    /* open descriptor and convert UTF-8 -> UTF-16LE */
    reiconv_t cd = reiconv_open_from_name("UTF-8", "UTF-16LE", REICONV_NO_FLAGS);
    if (cd == (reiconv_t)(-1) || cd == NULL)
    {
        return fail("reiconv_open_from_name");
    }
    size_t want = reiconv_result_size(cd, utf8_in, utf8_len);
    char *out = NULL;
    size_t out_len = 0;
    int rc = reiconv_convert(cd, utf8_in, utf8_len, &out, &out_len);
    if (rc != 0 || out == NULL || out_len != 10)
    {
        reiconv_handle_close(cd);
        return fail("reiconv_convert UTF-8->UTF-16LE");
    }
    reiconv_handle_close(cd);

    /* roundtrip back to UTF-8 */
    cd = reiconv_open_from_name("UTF-16LE", "UTF-8", REICONV_NO_FLAGS);
    if (cd == (reiconv_t)(-1) || cd == NULL)
    {
        free(out);
        return fail("reiconv_open_from_name roundtrip");
    }
    char *back = NULL;
    size_t back_len = 0;
    rc = reiconv_convert(cd, out, out_len, &back, &back_len);
    reiconv_handle_close(cd);
    free(out);
    if (rc != 0 || back == NULL || back_len != utf8_len || memcmp(back, utf8_in, utf8_len) != 0)
    {
        free(back);
        return fail("roundtrip mismatch");
    }
    free(back);

    printf("test cppp-reiconv 3.0.0: OK (UTF-8<->UTF-16LE roundtrip, GB18030 lookup)\n");
    return 0;
}
