/* tiledb test_package probe (R34: must call the tested library API).
 *
 * tiledb 2.30.1 C API:
 *   void   tiledb_version(int32_t* major, int32_t* minor, int32_t* rev)
 *   int32  tiledb_config_alloc(tiledb_config_t** config, tiledb_error_t** error)
 *   int32  tiledb_ctx_alloc_with_error(tiledb_config_t* config,
 *                                      tiledb_ctx_t** ctx, tiledb_error_t** error)
 *   void   tiledb_ctx_free(tiledb_ctx_t** ctx)
 *   void   tiledb_config_free(tiledb_config_t** config)
 *   void   tiledb_error_free(tiledb_error_t** error)
 * A version query + config/ctx alloc/free exercises the exported symbols
 * (proves libtiledb.so is linked and its symbols resolve at load time).
 */
#include <tiledb/tiledb.h>
#include <stdio.h>

static void report(const char *what, tiledb_error_t *err) {
    fprintf(stderr, "%s failed", what);
    if (err != NULL) {
        const char *msg = NULL;
        tiledb_error_message(err, &msg);
        if (msg != NULL) {
            fprintf(stderr, ": %s", msg);
        }
        tiledb_error_free(&err);
    }
    fprintf(stderr, "\n");
}

int main(void) {
    int32_t major = 0, minor = 0, rev = 0;
    tiledb_version(&major, &minor, &rev);
    printf("tiledb_version: %d.%d.%d\n", major, minor, rev);

    tiledb_config_t *config = NULL;
    tiledb_error_t *err = NULL;
    if (tiledb_config_alloc(&config, &err) != TILEDB_OK) {
        report("tiledb_config_alloc", err);
        return 1;
    }

    tiledb_ctx_t *ctx = NULL;
    if (tiledb_ctx_alloc_with_error(config, &ctx, &err) != TILEDB_OK) {
        report("tiledb_ctx_alloc_with_error", err);
        tiledb_config_free(&config);
        return 2;
    }
    tiledb_ctx_free(&ctx);
    if (ctx != NULL) {
        fprintf(stderr, "tiledb_ctx_free left non-null ctx\n");
        tiledb_config_free(&config);
        return 3;
    }

    tiledb_config_free(&config);
    if (config != NULL) {
        fprintf(stderr, "tiledb_config_free left non-null config\n");
        return 4;
    }

    printf("tiledb test_package probe: PASS\n");
    return 0;
}
