/*
 * test_iniparser.c — iniparser 4.2.6 consumer API round-trip test.
 *
 * R34 compliance: calls the real iniparser public API
 * (iniparser_load / iniparser_getstring / iniparser_getint /
 *  iniparser_set / iniparser_freedict / iniparser_getsecname etc.)
 * performing a full INI read/write round-trip:
 *   1. Write a temporary INI file
 *   2. Load it with iniparser_load
 *   3. Read back and verify values (string/int/boolean)
 *   4. Modify values with iniparser_set and verify
 *   5. Iterate sections with iniparser_getsecname
 *   6. Free the dictionary with iniparser_freedict
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <iniparser/iniparser.h>

static int failures = 0;

#define CHECK(cond, msg)                            \
    do {                                            \
        if (!(cond)) {                              \
            fprintf(stderr, "FAIL: %s\n", msg);     \
            failures++;                             \
        } else {                                    \
            printf("PASS: %s\n", msg);              \
        }                                           \
    } while (0)

int main(void)
{
    const char *ini_path;
    dictionary *ini;
    const char *str;
    int val;
    FILE *f;
    int i;
    int nsec;

    ini_path = getenv("TEST_INI_PATH");
    if (ini_path == NULL || ini_path[0] == '\0') {
        ini_path = "test.ini";
    }

    /* 1. Create a source INI file */
    f = fopen(ini_path, "w");
    if (f == NULL) {
        perror("fopen");
        return 2;
    }
    fprintf(f,
            "[Pizza]\n"
            "Ham = yes ; with comment\n"
            "Mushrooms = TRUE\n"
            "Capres = 0\n"
            "Cheese = Non\n"
            "Weight = 7\n"
            "Empty =\n"
            "\n"
            "[Wine]\n"
            "Grape = Cabernet Sauvignon\n"
            "Year = 1989\n"
            "Alcohol = 12.5\n");
    fclose(f);

    /* 2. Load with iniparser_load */
    ini = iniparser_load(ini_path);
    CHECK(ini != NULL, "iniparser_load parses the test file");

    if (ini == NULL) {
        return 1;
    }

    /* 3. Read back and verify values */
    str = iniparser_getstring(ini, "Pizza:Ham", "MISSING");
    CHECK(str != NULL && strcmp(str, "yes") == 0,
          "iniparser_getstring Pizza:Ham == 'yes'");

    str = iniparser_getstring(ini, "Wine:Grape", "MISSING");
    CHECK(str != NULL && strcmp(str, "Cabernet Sauvignon") == 0,
          "iniparser_getstring Wine:Grape round-trips");

    val = iniparser_getint(ini, "Wine:Year", -1);
    CHECK(val == 1989, "iniparser_getint Wine:Year == 1989");

    val = iniparser_getint(ini, "Pizza:Weight", -1);
    CHECK(val == 7, "iniparser_getint Pizza:Weight == 7");

    val = iniparser_getboolean(ini, "Pizza:Mushrooms", -1);
    CHECK(val == 1, "iniparser_getboolean Pizza:Mushrooms == 1 (TRUE)");

    val = iniparser_getboolean(ini, "Pizza:Capres", -1);
    CHECK(val == 0, "iniparser_getboolean Pizza:Capres == 0");

    /* Missing keys fall back to default */
    str = iniparser_getstring(ini, "Pizza:DoesNotExist", "fallback");
    CHECK(str != NULL && strcmp(str, "fallback") == 0,
          "missing key returns default (not-found handling)");

    val = iniparser_getint(ini, "Pizza:DoesNotExist", -42);
    CHECK(val == -42, "missing int key returns default -42");

    /* 4. Modify and verify with iniparser_set */
    val = iniparser_set(ini, "Wine:Year", "2001");
    CHECK(val == 0, "iniparser_set Wine:Year=2001 succeeds");
    val = iniparser_getint(ini, "Wine:Year", -1);
    CHECK(val == 2001, "modified value reads back as 2001");

    val = iniparser_set(ini, "Wine:Region", "Bordeaux");
    CHECK(val == 0, "iniparser_set creates new key Wine:Region");
    str = iniparser_getstring(ini, "Wine:Region", "MISSING");
    CHECK(str != NULL && strcmp(str, "Bordeaux") == 0,
          "newly created key reads back correctly");

    /* 5. Section iteration */
    nsec = iniparser_getnsec(ini);
    CHECK(nsec == 2, "iniparser_getnsec == 2");
    /* NOTE: iniparser stores section names lowercased internally;
     * getsecname returns the normalized (lowercase) name. */
    str = iniparser_getsecname(ini, 0);
    CHECK(str != NULL && strcmp(str, "pizza") == 0,
          "iniparser_getsecname(0) == pizza (lowercase normalized)");
    str = iniparser_getsecname(ini, 1);
    CHECK(str != NULL && strcmp(str, "wine") == 0,
          "iniparser_getsecname(1) == wine (lowercase normalized)");

    /* Number of keys in a section */
    val = iniparser_getsecnkeys(ini, "Pizza");
    CHECK(val == 6, "iniparser_getsecnkeys Pizza == 6");

    /* 6. Free */
    iniparser_freedict(ini);
    CHECK(1, "iniparser_freedict completes without crash");

    /* Reload after free — library remains usable */
    ini = iniparser_load(ini_path);
    CHECK(ini != NULL, "library reusable after freedict");
    if (ini != NULL) {
        iniparser_freedict(ini);
    }

    /* Clean up */
    remove(ini_path);

    if (failures > 0) {
        fprintf(stderr, "%d assertion(s) failed\n", failures);
        return 1;
    }
    printf("all iniparser round-trip assertions passed\n");
    return 0;
}
