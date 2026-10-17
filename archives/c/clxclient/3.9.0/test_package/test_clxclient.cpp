#include <cstdio>
#include <cstring>

#include "clxclient.h"

/*
 * Exercise the packaged libclxclient through real, display-independent API:
 * X_resman parses an X resource database (Xrm*) without opening a display
 * connection. All calls below resolve to non-inline symbols in
 * libclxclient, so a missing export fails at link time (R34).
 */

static XrmOptionDescRec g_options[] = {
    { (char *)"-geometry", (char *)"*geometry", XrmoptionSepArg, NULL },
    { (char *)"-title", (char *)"*title", XrmoptionSepArg, NULL },
};

int main(void)
{
    int discovered = 3;
    int passed = 0;

    // A resource database built from the command line works without any
    // X display: XrmParseCommand feeds *geometry/*title, and get() reads
    // them straight back through the packaged library.
    X_resman resman;
    char *argv[] = {
        (char *)"clxtest",
        (char *)"-geometry", (char *)"1024x768",
        (char *)"-title", (char *)"Clxclient-Integration",
        NULL,
    };
    int argc = 5;
    resman.init(&argc, argv, (char *)"clxtest", g_options, 2);

    const char *geometry = nullptr;
    const char *title = nullptr;

    printf("Test 1: X_resman geometry round-trip ... ");
    geometry = resman.get(".geometry", "640x480");
    if (std::strcmp(geometry, "1024x768") != 0) {
        printf("FAIL (got %s)\n", geometry);
        goto report;
    }
    printf("OK\n");
    passed++;

    printf("Test 2: X_resman title round-trip ... ");
    title = resman.get(".title", "unset");
    if (std::strcmp(title, "Clxclient-Integration") != 0) {
        printf("FAIL (got %s)\n", title);
        goto report;
    }
    printf("OK\n");
    passed++;

    printf("Test 3: X_resman getb default ... ");
    if (resman.getb(".mono", 1) != 1) {
        printf("FAIL\n");
        goto report;
    }
    printf("OK\n");
    passed++;

report:
    bool ok = (passed == discovered);
    printf(
        "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,"
        "\"command\":\"./test_clxclient\",\"discovered\":%d,\"passedCount\":%d}\n",
        ok ? "true" : "false", discovered, passed);
    printf("Consumer test: %d/%d passed\n", passed, discovered);
    return ok ? 0 : 1;
}
