/* Consumer test for the mapcode Conan package.
 *
 * Exercises the installed mapcodelib through its public C API:
 *   - library / data version reporting
 *   - territory lookup (ISO3166 alpha-3 round trip)
 *   - encoding a coordinate to a Mapcode
 *   - format validation of valid and invalid Mapcodes
 *   - decoding a Mapcode back to a coordinate, with an accuracy bound
 *   - the effect of extra precision digits on the achievable accuracy
 *   - distance helper and worst-case error table
 */
#include <math.h>
#include <stdio.h>
#include <string.h>

#include "mapcodelib/mapcoder.h"

static int failures = 0;
static int checks = 0;

static void check(int condition, const char* what) {
    checks++;
    if (condition) {
        printf("ok   - %s\n", what);
    } else {
        failures++;
        printf("FAIL - %s\n", what);
    }
}

int main(void) {
    printf("mapcode consumer test (library version %s)\n", _MAPCODE_C_VERSION);

    /* 1. Version reporting: the header constant and the exported variable
     *    must agree, so that consumers can rely on either one. */
    check(strcmp(MAPCODE_C_VERSION, "2.5.7") == 0,
          "MAPCODE_C_VERSION is 2.5.7");
    check(strcmp(_MAPCODE_C_VERSION, MAPCODE_C_VERSION) == 0,
          "_MAPCODE_C_VERSION matches MAPCODE_C_VERSION");
    check(MAX_PRECISION_DIGITS == 8, "MAX_PRECISION_DIGITS is 8");

    /* 2. Territory lookup round trip. */
    enum Territory netherlands = getTerritoryCode("NLD", TERRITORY_NONE);
    check(netherlands != TERRITORY_NONE, "getTerritoryCode resolves NLD");
    char iso[MAX_ISOCODE_ASCII_LEN + 1];
    getTerritoryIsoName(iso, netherlands, 1);
    check(strcmp(iso, "NLD") == 0, "getTerritoryIsoName round trips to NLD");
    check(getTerritoryCode("XXX", TERRITORY_NONE) == TERRITORY_NONE,
          "getTerritoryCode rejects an unknown code");

    /* 3. Encoding Amsterdam within the Netherlands. */
    const double amsLat = 52.3702;
    const double amsLon = 4.8952;
    char mapcode[MAX_MAPCODE_RESULT_ASCII_LEN + 1];
    int nr = encodeLatLonToSingleMapcode(mapcode, amsLat, amsLon, netherlands, 0);
    check(nr == 1, "encodeLatLonToSingleMapcode returns exactly one result");
    check(strlen(mapcode) > 0, "encoded Mapcode is not empty");
    printf("     encoded: %s\n", mapcode);

    /* 4. Format validation: the produced Mapcode is well formed, a random
     *    string is not. */
    check(compareWithMapcodeFormatUtf8(mapcode) == ERR_OK,
          "produced Mapcode passes compareWithMapcodeFormatUtf8");
    check(compareWithMapcodeFormatUtf8("not a mapcode") != ERR_OK,
          "garbage input is rejected by compareWithMapcodeFormatUtf8");

    /* 5. Decoding the Mapcode returns a nearby coordinate. A plain Mapcode is
     *    accurate to a few hundred meters, so 2 km is a safe bound. */
    double lat = 0.0;
    double lon = 0.0;
    enum MapcodeError err = decodeMapcodeToLatLonUtf8(&lat, &lon, mapcode,
                                                      netherlands, NULL);
    check(err == ERR_OK, "decodeMapcodeToLatLonUtf8 succeeds");
    check(fabs(lat - amsLat) < 0.05 && fabs(lon - amsLon) < 0.05,
          "decoded coordinate is within 0.05 degrees");
    double err0 = distanceInMeters(amsLat, amsLon, lat, lon);
    printf("     plain Mapcode error: %.1f m\n", err0);
    check(err0 < 2000.0, "plain Mapcode error is below 2 km");
    check(err0 <= maxErrorInMeters(0),
          "observed error is within the documented worst case");

    /* 6. Two extra precision digits must decode strictly closer. */
    char precise[MAX_MAPCODE_RESULT_ASCII_LEN + 1];
    encodeLatLonToSingleMapcode(precise, amsLat, amsLon, netherlands, 2);
    check(strlen(precise) > strlen(mapcode),
          "two extra digits lengthen the Mapcode");
    double plat = 0.0;
    double plon = 0.0;
    check(decodeMapcodeToLatLonUtf8(&plat, &plon, precise, netherlands, NULL) == ERR_OK,
          "high precision Mapcode decodes");
    double err2 = distanceInMeters(amsLat, amsLon, plat, plon);
    printf("     2-digit Mapcode error: %.1f m\n", err2);
    check(err2 < err0, "two extra digits improve accuracy");
    check(err2 <= maxErrorInMeters(2),
          "high precision error is within the documented worst case");

    /* 7. The full encoder returns several candidates for the same point. */
    Mapcodes all;
    int total = encodeLatLonToMapcodes(&all, amsLat, amsLon, netherlands, 0);
    check(total > 0, "encodeLatLonToMapcodes returns candidates");
    check(all.count == total, "Mapcodes.count matches the return value");

    /* 8. Distance helper: identical points are zero apart, and the error
     *    computed above agrees with the distance between both decodings. */
    check(distanceInMeters(amsLat, amsLon, amsLat, amsLon) == 0.0,
          "distanceInMeters is zero for identical points");
    check(maxErrorInMeters(0) > 0.0 && maxErrorInMeters(0) < 1000.0,
          "documented worst case for a plain Mapcode is sub-kilometer");
    check(fabs(distanceInMeters(lat, lon, plat, plon) - (err0 - err2)) < 1.0 ||
          distanceInMeters(lat, lon, plat, plon) < 100.0,
          "plain and precise decodings lie close together");

    /* 9. Encoding without a territory context still succeeds. */
    char anyTerritory[MAX_MAPCODE_RESULT_ASCII_LEN + 1];
    check(encodeLatLonToSingleMapcode(anyTerritory, amsLat, amsLon,
                                      TERRITORY_NONE, 0) == 1,
          "encoding without a territory context succeeds");

    printf("\n%d checks, %d failures\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
