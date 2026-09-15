/* Consumer contract test for the OpenDBX 1.4.6 C API (libopendbx).
 *
 * No database server is needed: every check exercises handle validation,
 * error reporting and library metadata paths that work without a backend.
 * Each CHECK prints PASS/FAIL; the summary line carries the exact counts.
 */
#include <stdio.h>
#include <string.h>

#include <odbx.h>

static int passed = 0;
static int failed = 0;

#define CHECK(cond, name)                                                     \
    do {                                                                      \
        if (cond) {                                                           \
            printf("PASS: %s\n", name);                                       \
            ++passed;                                                         \
        } else {                                                              \
            printf("FAIL: %s\n", name);                                       \
            ++failed;                                                         \
        }                                                                     \
    } while (0)

int main(void)
{
    odbx_t* handle = NULL;
    int rc;
    int libver = 0;
    char out[64];
    unsigned long outlen = sizeof(out);
    const char* msg;

    /* odbx_init validates its parameters before touching anything. */
    rc = odbx_init(NULL, "sqlite3", "./", "");
    CHECK(rc == -ODBX_ERR_PARAM, "init-null-handle-param");
    rc = odbx_init(&handle, NULL, "./", "");
    CHECK(rc == -ODBX_ERR_PARAM, "init-null-backend-param");
    CHECK(handle == NULL, "init-param-leaves-handle-null");

    /* Unknown backend exercises the dlopen() failure branch. */
    rc = odbx_init(&handle, "opendbx_hmos_probe_backend", "./", "");
    CHECK(rc == -ODBX_ERR_NOTEXIST, "init-unknown-backend-notexist");

    /* Error reporting works without a handle. */
    msg = odbx_error(NULL, -ODBX_ERR_HANDLE);
    CHECK(msg != NULL && msg[0] != '\0', "error-message-nonempty");
    CHECK(strcmp(msg, odbx_error(NULL, -ODBX_ERR_HANDLE)) == 0, "error-message-stable");
    CHECK(odbx_error_type(NULL, -ODBX_ERR_HANDLE) == -1, "error-type-fatal");
    CHECK(odbx_error_type(NULL, ODBX_ERR_SUCCESS) == 0, "error-type-success-zero");

    /* Library version is readable without a connection. Upstream builds
     * with -DLIBVERSION=10406 (decimal for 1.4.6); compare as decimal,
     * NOT as C octal literal 010406 (which would be 4358). */
    rc = odbx_get_option(NULL, ODBX_OPT_LIB_VERSION, &libver);
    CHECK(rc == ODBX_ERR_SUCCESS && libver == 10406, "lib-version-010406");
    rc = odbx_get_option(NULL, ODBX_OPT_LIB_VERSION, NULL);
    CHECK(rc == -ODBX_ERR_PARAM, "get-option-null-value-param");

    /* Null-handle guards on the remaining entry points. */
    CHECK(odbx_capabilities(NULL, ODBX_CAP_BASIC) == -ODBX_ERR_HANDLE,
          "capabilities-null-handle");
    CHECK(odbx_finish(NULL) == -ODBX_ERR_HANDLE, "finish-null-handle");
    CHECK(odbx_unbind(NULL) == -ODBX_ERR_HANDLE, "unbind-null-handle");
    CHECK(odbx_escape(NULL, "a'b", 3, out, &outlen) == -ODBX_ERR_HANDLE,
          "escape-null-handle");

    printf("test_opendbx: %d passed, %d failed\n", passed, failed);
    return failed ? 1 : 0;
}
