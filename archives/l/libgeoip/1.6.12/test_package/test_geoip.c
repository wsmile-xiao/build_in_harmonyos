/* test_package/test_geoip.c — consumer-side functional test for
 * libgeoip 1.6.12 (libGeoIP) on HarmonyOS PC.
 *
 * Mirrors the upstream test/test-geoip.c flow (country lookups against
 * the sample GeoIP.dat shipped inside the upstream tarball) but from
 * the *consumer* perspective: it links against the conan-packaged
 * libGeoIP and reads GeoIP.dat from the test_package source dir.
 *
 * Checks (R34: real API usage, no stubs):
 *   1. GeoIP_open(GEOIP_MEMORY_CACHE) on the sample country database
 *   2. GeoIP_database_info returns the expected build banner
 *   3. GeoIP_country_code_by_addr/name + code3 lookups for every entry
 *      of the upstream country_test.txt vector set (61 IPs)
 *   4. invalid queries (NULL name) handled gracefully -> NULL
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <GeoIP.h>

#define CHECK(cond, msg)                                                   \
    do {                                                                   \
        if (!(cond)) {                                                     \
            fprintf(stderr, "FAIL: %s\n", msg);                            \
            return 1;                                                      \
        }                                                                  \
    } while (0)

static const char *DB_INFO_EXPECTED =
    "GEO-106 20160621 Build 1 Copyright (c) 2016 MaxMind Inc All Rights "
    "Reserved";

int main(int argc, char **argv)
{
    const char *dat_path = argc > 1 ? argv[1] : "GeoIP.dat";
    const char *vec_path = argc > 2 ? argv[2] : "country_test.txt";
    char ipAddress[64];
    char expectedCountry[8];
    char expectedCountry3[8];
    const char *returnedCountry;
    GeoIP *gi;
    char *db_info;
    int fails = 0;
    int cases = 0;
    FILE *f;

    /* --- 1. open sample database (memory cache, like upstream test) --- */
    gi = GeoIP_open(dat_path, GEOIP_MEMORY_CACHE);
    CHECK(gi != NULL, "GeoIP_open(GEOIP_MEMORY_CACHE) on sample GeoIP.dat");

    /* --- 2. database info banner --- */
    db_info = GeoIP_database_info(gi);
    CHECK(db_info != NULL && strcmp(db_info, DB_INFO_EXPECTED) == 0,
          "GeoIP_database_info matches upstream build banner");
    free(db_info);

    /* --- 3. invalid queries handled gracefully --- */
    CHECK(GeoIP_country_code_by_addr(gi, NULL) == NULL,
          "GeoIP_country_code_by_addr(NULL) returns NULL");
    CHECK(GeoIP_country_code_by_name(gi, NULL) == NULL,
          "GeoIP_country_code_by_name(NULL) returns NULL");

    /* --- 4. full upstream country_test.txt vector set --- */
    f = fopen(vec_path, "r");
    CHECK(f != NULL, "open country_test.txt vector file");
    while (fscanf(f, "%63s%7s%7s", ipAddress, expectedCountry,
                  expectedCountry3) != EOF) {
        returnedCountry = GeoIP_country_code_by_addr(gi, ipAddress);
        if (returnedCountry == NULL ||
            strcmp(returnedCountry, expectedCountry) != 0) {
            fprintf(stderr,
                    "addr lookup failed for %s: got %s, expected %s\n",
                    ipAddress,
                    returnedCountry ? returnedCountry : "()",
                    expectedCountry);
            fails++;
        }
        returnedCountry = GeoIP_country_code_by_name(gi, ipAddress);
        if (returnedCountry == NULL ||
            strcmp(returnedCountry, expectedCountry) != 0) {
            fprintf(stderr,
                    "name lookup failed for %s: got %s, expected %s\n",
                    ipAddress,
                    returnedCountry ? returnedCountry : "()",
                    expectedCountry);
            fails++;
        }
        returnedCountry = GeoIP_country_code3_by_addr(gi, ipAddress);
        if (returnedCountry == NULL ||
            strcmp(returnedCountry, expectedCountry3) != 0) {
            fprintf(stderr,
                    "addr code3 lookup failed for %s: got %s, expected %s\n",
                    ipAddress,
                    returnedCountry ? returnedCountry : "()",
                    expectedCountry3);
            fails++;
        }
        cases++;
    }
    fclose(f);
    GeoIP_delete(gi);

    CHECK(cases == 61, "processed all 61 upstream vector entries");
    CHECK(fails == 0, "all country lookups returned expected values");

    /* --- 5. filesystem mode (GEOIP_STANDARD | GEOIP_CHECK_CACHE) --- */
    gi = GeoIP_open(dat_path, GEOIP_STANDARD | GEOIP_CHECK_CACHE);
    CHECK(gi != NULL, "GeoIP_open(GEOIP_STANDARD|GEOIP_CHECK_CACHE)");
    returnedCountry = GeoIP_country_code_by_addr(gi, "12.87.118.0");
    CHECK(returnedCountry != NULL && strcmp(returnedCountry, "US") == 0,
          "filesystem-mode lookup 12.87.118.0 == US");
    returnedCountry = GeoIP_country_code_by_addr(gi, "63.147.126.103");
    CHECK(returnedCountry != NULL && strcmp(returnedCountry, "FR") == 0,
          "filesystem-mode lookup 63.147.126.103 == FR");
    GeoIP_delete(gi);

    printf("PASS: libgeoip consumer test (%d vector IPs, 0 failures)\n",
           cases);
    return 0;
}
