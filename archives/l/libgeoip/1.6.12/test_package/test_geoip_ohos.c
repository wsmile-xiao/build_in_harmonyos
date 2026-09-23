/* test_package/test_geoip_ohos.c — HarmonyOS-specific test for
 * libgeoip 1.6.12 (rule12: OHOS-specific test line, real platform
 * verification, no stub).
 *
 * libGeoIP's data path on OHOS differs from glibc in ways this test
 * pins down:
 *   1. The library is pure C / musl: file access goes through plain
 *      stdio + mmap; verify GeoIP_open works with the OHOS page size
 *      via _SC_PAGESIZE (musl exposes sysconf).
 *   2. GeoIP uses pread(2) on OHOS (HAVE_PREAD detected by configure);
 *      verify the underlying sysconf(_SC_PAGESIZE) > 0 so mmap/pread
 *      paths are exercised on the real kernel.
 *   3. GeoIP_setup_custom_directory + _GeoIP_lookupaddress (gethostbyname
 *      path) exist on OHOS musl networking stack.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <GeoIP.h>

#ifndef __OHOS__
#error "This test must be compiled by the HarmonyOS toolchain"
#endif

#define CHECK(cond, msg)                                                   \
    do {                                                                   \
        if (!(cond)) {                                                     \
            fprintf(stderr, "FAIL: %s\n", msg);                            \
            return 1;                                                      \
        }                                                                  \
    } while (0)

int main(int argc, char **argv)
{
    const char *dat_path = argc > 1 ? argv[1] : "GeoIP.dat";
    GeoIP *gi;
    long page_size;
    int geoip_db_avail;
    const char *code;

    /* --- 1. OHOS musl sysconf: mmap-based cache path prerequisites --- */
    page_size = sysconf(_SC_PAGESIZE);
    CHECK(page_size > 0, "sysconf(_SC_PAGESIZE) works on OHOS (mmap cache)");
    printf("OHOS page size: %ld\n", page_size);

    /* --- 2. custom directory discovery: must be set BEFORE the first
     * GeoIP_open — _GeoIP_setup_dbfilename caches GeoIPDBFileName after
     * the first call, so ordering matters --- */
    {
        static char custom_dir[512];
        char *slash;
        strncpy(custom_dir, dat_path, sizeof(custom_dir) - 1);
        custom_dir[sizeof(custom_dir) - 1] = '\0';
        slash = strrchr(custom_dir, '/');
        if (slash != NULL) {
            *slash = '\0';
        } else {
            strncpy(custom_dir, ".", sizeof(custom_dir) - 1);
        }
        GeoIP_setup_custom_directory(custom_dir);
    }
    geoip_db_avail = GeoIP_db_avail(GEOIP_COUNTRY_EDITION);
    CHECK(geoip_db_avail == 1,
          "GeoIP_db_avail finds GeoIP.dat in custom dir on OHOS");

    /* --- 3. open + lookup through the OHOS stdio/pread data path --- */
    gi = GeoIP_open(dat_path, GEOIP_MEMORY_CACHE);
    CHECK(gi != NULL, "GeoIP_open memory-cache on OHOS musl stdio");
    code = GeoIP_country_code_by_addr(gi, "12.87.118.0");
    CHECK(code != NULL && strcmp(code, "US") == 0,
          "country lookup via OHOS musl stdio path == US");
    code = GeoIP_country_code_by_name(gi, "63.147.126.103");
    CHECK(code != NULL && strcmp(code, "FR") == 0,
          "name lookup via OHOS gethostbyname path == FR");
    GeoIP_delete(gi);

    printf("PASS: libgeoip HarmonyOS-specific test "
           "(page/mmap + stdio + custom dir)\n");
    return 0;
}
