/* test_package for postgresql 16.10 — real libpq API validation (R34).
 *
 * Calls PQlibVersion() (a pure-local API that needs no server connection)
 * and asserts the major version is 16 — proving libpq is linkable and
 * functional. Extending/loading server-side .so modules is intentionally
 * avoided: the OHOS ELF signing mechanism blocks dlopen of unsigned
 * shared objects (historical opr_sanity failure, a known platform
 * limitation, see notes.md).
 */
#include <libpq-fe.h>
#include <stdio.h>

int main(void)
{
    int v = PQlibVersion();
    /* PG_VERSION_NUM encoding since v10: major*10000 + minor (160010 = 16.10). */
    int major = v / 10000;
    int minor = v % 10000;
    printf("PQlibVersion() = %d\n", v);
    if (major != 16) {
        fprintf(stderr, "FAIL: expected libpq major 16, got %d\n", major);
        return 1;
    }
    printf("PASS: linked and executed against libpq %d.%d\n", major, minor);
    return 0;
}
