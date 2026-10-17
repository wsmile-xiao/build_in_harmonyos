/*
 * libconfigini consumer test — Conan L1 official test (R34).
 *
 * Simulates a business component that parses an INI configuration file
 * through the installed public API (src/configini.h): reads sections/keys,
 * checks values, then edits and re-saves the file. Uses only public API
 * and normal link targets (libconfigini.a).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "configini.h"

#define CHECK(cond, msg) do { \
    if (!(cond)) { \
        fprintf(stderr, "FAIL: %s (%s:%d)\n", msg, __FILE__, __LINE__); \
        exit(1); \
    } \
} while (0)

int main(void)
{
    Config *cfg = NULL;
    char s[256];

    /* Build a config in memory via public API */
    cfg = ConfigNew();
    CHECK(cfg != NULL, "ConfigNew");

    CHECK(ConfigAddString(cfg, "app", "name", "demo") == CONFIG_OK, "ConfigAddString");
    CHECK(ConfigAddInt(cfg, "app", "port", 8080) == CONFIG_OK, "ConfigAddInt");
    CHECK(ConfigAddBool(cfg, "app", "debug", true) == CONFIG_OK, "ConfigAddBool");
    CHECK(ConfigAddDouble(cfg, "app", "ratio", 0.5) == CONFIG_OK, "ConfigAddDouble");
    CHECK(ConfigHasSection(cfg, "app"), "ConfigHasSection");
    CHECK(ConfigGetSectionCount(cfg) >= 1, "ConfigGetSectionCount");
    CHECK(ConfigGetKeyCount(cfg, "app") == 4, "ConfigGetKeyCount");

    /* Read back through public read API */
    CHECK(ConfigReadString(cfg, "app", "name", s, sizeof(s), "") == CONFIG_OK, "ConfigReadString");
    CHECK(strcmp(s, "demo") == 0, "name == demo");

    int port = 0;
    CHECK(ConfigReadInt(cfg, "app", "port", &port, -1) == CONFIG_OK, "ConfigReadInt");
    CHECK(port == 8080, "port == 8080");

    bool debug = false;
    CHECK(ConfigReadBool(cfg, "app", "debug", &debug, false) == CONFIG_OK, "ConfigReadBool");
    CHECK(debug == true, "debug == true");

    double ratio = 0.0;
    CHECK(ConfigReadDouble(cfg, "app", "ratio", &ratio, 0.0) == CONFIG_OK, "ConfigReadDouble");
    CHECK(ratio > 0.49 && ratio < 0.51, "ratio ~= 0.5");

    /* Save to a file, read back, and verify a fresh parse */
    CHECK(ConfigPrintToFile(cfg, "consumer-test.cnf") == CONFIG_OK, "ConfigPrintToFile");
    ConfigFree(cfg);

    cfg = NULL;
    CHECK(ConfigReadFile("consumer-test.cnf", &cfg) == CONFIG_OK, "ConfigReadFile roundtrip");
    CHECK(ConfigReadString(cfg, "app", "name", s, sizeof(s), "") == CONFIG_OK
          && strcmp(s, "demo") == 0, "roundtrip name");
    ConfigFree(cfg);

    printf("libconfigini consumer test: OK\n");
    return 0;
}
