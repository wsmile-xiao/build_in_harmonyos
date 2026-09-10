#include <stdio.h>
#include <string.h>
#include <stdlib.h>

#include "ClearSilver.h"
#include "util/neo_hdf.h"
#include "util/neo_str.h"
#include "cs/cs.h"

static NEOERR *output_cb(void *ctx, char *s)
{
    STRING *out = (STRING *)ctx;
    if (!out || !s) return STATUS_OK;
    /* string_append may fail on OOM, but for smoke we ignore NERR */
    string_append(out, s);
    return STATUS_OK;
}

int main(void)
{
    /* HMBS readonly /tmp compat: ensure TMPDIR/TMP/TEMP point to writable location
       when running on HarmonyOS (HMBS injects per-task tmpdir). Test itself does
       not write to /tmp, but ensure env is valid for any indirect mktemp. */
    const char *tmp = getenv("HMBS_TMPDIR");
    if (!tmp) tmp = getenv("TMPDIR");
    if (!tmp) tmp = getenv("TMP");
    if (!tmp) tmp = getenv("TEMP");
    (void)tmp;

    NEOERR *err;
    HDF *hdf = NULL;
    CSPARSE *parse = NULL;
    /* Use heap-allocated copy: cs_parse_string takes ownership and mutates/frees buf */
    const char *tmpl_const = "Hello <?cs var:Query.var ?>! Value=<?cs var:Data.num ?>\n<?cs if:Query.show ?>SHOW<?cs else ?>HIDE<?cs /if ?>";
    char *tmpl = NULL;
    STRING outbuf;
    const char *expected_sub = "Hello hello!";

    string_init(&outbuf);

    err = hdf_init(&hdf);
    if (err != STATUS_OK) {
        nerr_log_error(err);
        fprintf(stderr, "hdf_init failed\n");
        return 1;
    }
    err = hdf_set_value(hdf, "Query.var", "hello");
    if (err != STATUS_OK) { nerr_log_error(err); return 1; }
    err = hdf_set_value(hdf, "Data.num", "42");
    if (err != STATUS_OK) { nerr_log_error(err); return 1; }
    err = hdf_set_value(hdf, "Query.show", "1");
    if (err != STATUS_OK) { nerr_log_error(err); return 1; }

    {
        char *v = hdf_get_value(hdf, "Query.var", NULL);
        if (!v || strcmp(v, "hello") != 0) {
            fprintf(stderr, "hdf_get_value mismatch: %s\n", v ? v : "NULL");
            return 1;
        }
        printf("HDF test passed: Query.var=%s\n", v);
    }

    err = cs_init(&parse, hdf);
    if (err != STATUS_OK) {
        nerr_log_error(err);
        fprintf(stderr, "cs_init failed\n");
        return 1;
    }

    tmpl = strdup(tmpl_const);
    if (!tmpl) {
        fprintf(stderr, "strdup failed\n");
        return 1;
    }
    err = cs_parse_string(parse, tmpl, strlen(tmpl));
    if (err != STATUS_OK) {
        nerr_log_error(err);
        fprintf(stderr, "cs_parse_string failed\n");
        /* tmpl ownership transferred to parse on success only; on failure we must free */
        free(tmpl);
        return 1;
    }
    /* ownership transferred to parse, will be freed by cs_destroy */

    err = cs_render(parse, &outbuf, output_cb);
    if (err != STATUS_OK) {
        nerr_log_error(err);
        fprintf(stderr, "cs_render failed\n");
        return 1;
    }

    printf("Rendered: %s\n", outbuf.buf ? outbuf.buf : "(null)");
    if (!outbuf.buf || strstr(outbuf.buf, expected_sub) == NULL) {
        fprintf(stderr, "render output missing expected substring '%s'\n", expected_sub);
        return 1;
    }
    if (strstr(outbuf.buf, "SHOW") == NULL) {
        fprintf(stderr, "conditional render failed: SHOW not found\n");
        return 1;
    }
    if (strstr(outbuf.buf, "42") == NULL) {
        fprintf(stderr, "render missing Data.num\n");
        return 1;
    }

    cs_destroy(&parse);
    hdf_destroy(&hdf);
    string_clear(&outbuf);

    /* second test: HDF hierarchy */
    err = hdf_init(&hdf);
    if (err != STATUS_OK) { nerr_log_error(err); return 1; }
    err = hdf_set_value(hdf, "A.B.C", "123");
    if (err != STATUS_OK) { nerr_log_error(err); return 1; }
    {
        char *got = hdf_get_value(hdf, "A.B.C", NULL);
        if (!got || strcmp(got, "123") != 0) {
            fprintf(stderr, "second HDF test failed: got %s\n", got ? got : "NULL");
            return 1;
        }
        printf("HDF hierarchy test passed: A.B.C=%s\n", got);
    }
    hdf_destroy(&hdf);
    printf("All clearsilver API tests passed\n");
    return 0;
}
