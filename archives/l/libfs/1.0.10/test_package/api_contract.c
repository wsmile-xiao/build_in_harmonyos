#include <X11/fonts/FSlib.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/*
 * Deterministic installed-package checks for libFS 1.0.10.
 *
 * Every assertion uses only the public FSlib.h API and never needs a
 * running font server: server-name resolution is exercised through the
 * documented precedence rules, the allocation helpers through a byte
 * pattern round-trip, the list destructors through their NULL
 * contracts, and FSOpenServer through its documented NULL return for
 * unreachable transports (asserted as the expected result, never
 * treated as an incidental pass).
 */

static const char env_sentinel[] =
    "invalid-transport-env/sentinel.invalid:7100";
static const char explicit_server[] =
    "invalid-transport-explicit/sentinel.invalid:7100";
static const char unknown_transport[] =
    "invalid-transport-unknown/sentinel.invalid:7100";

static int check_fsservername(void)
{
    const char *resolved;

    if (setenv("FONTSERVER", env_sentinel, 1) != 0) {
        fprintf(stderr, "setenv(FONTSERVER) failed\n");
        return 1;
    }
    resolved = FSServerName(NULL);
    if (resolved == NULL || strcmp(resolved, env_sentinel) != 0) {
        fprintf(stderr, "FSServerName(NULL) ignored FONTSERVER\n");
        return 2;
    }
    resolved = FSServerName("");
    if (resolved == NULL || strcmp(resolved, env_sentinel) != 0) {
        fprintf(stderr, "FSServerName(\\\"\\\") ignored FONTSERVER\n");
        return 3;
    }
    resolved = FSServerName(explicit_server);
    if (resolved == NULL || strcmp(resolved, explicit_server) != 0) {
        fprintf(stderr, "FSServerName(server) did not return the explicit server\n");
        return 4;
    }
    if (unsetenv("FONTSERVER") != 0) {
        fprintf(stderr, "unsetenv(FONTSERVER) failed\n");
        return 5;
    }
    if (FSServerName(NULL) != NULL) {
        fprintf(stderr, "FSServerName(NULL) must be NULL without FONTSERVER\n");
        return 6;
    }
    if (FSServerName("") != NULL) {
        fprintf(stderr, "FSServerName(empty) must be NULL without FONTSERVER\n");
        return 7;
    }
    return 0;
}

static int check_allocation(void)
{
    unsigned char *buffer;
    unsigned index;

    buffer = FSMalloc(256);
    if (buffer == NULL) {
        fprintf(stderr, "FSMalloc(256) returned NULL\n");
        return 8;
    }
    for (index = 0; index < 256; ++index)
        buffer[index] = (unsigned char)(index * 7 + 3);
    for (index = 0; index < 256; ++index) {
        if (buffer[index] != (unsigned char)(index * 7 + 3)) {
            fprintf(stderr, "FSMalloc buffer corrupted at offset %u\n", index);
            return 9;
        }
    }
    if (FSFree((char *)buffer) != 1) {
        fprintf(stderr, "FSFree(buffer) did not return 1\n");
        return 10;
    }
    if (FSFree(NULL) != 1) {
        fprintf(stderr, "FSFree(NULL) did not return 1\n");
        return 11;
    }
    return 0;
}

static int check_null_safe_destructors(void)
{
    if (FSFreeFontNames(NULL) != 1) {
        fprintf(stderr, "FSFreeFontNames(NULL) did not return 1\n");
        return 12;
    }
    if (FSFreeCatalogues(NULL) != 1) {
        fprintf(stderr, "FSFreeCatalogues(NULL) did not return 1\n");
        return 13;
    }
    if (FSFreeExtensionList(NULL) != 1) {
        fprintf(stderr, "FSFreeExtensionList(NULL) did not return 1\n");
        return 14;
    }
    return 0;
}

static int check_fsopenserver_failure_contract(void)
{
    FSServer *server;

    (void)unsetenv("FONTSERVER");

    server = FSOpenServer("");
    if (server != NULL) {
        fprintf(stderr, "FSOpenServer(empty) must fail without FONTSERVER\n");
        return 15;
    }

    server = FSOpenServer(unknown_transport);
    if (server != NULL) {
        fprintf(stderr, "FSOpenServer must fail for an unknown transport\n");
        return 16;
    }

    if (setenv("FONTSERVER", env_sentinel, 1) != 0) {
        fprintf(stderr, "setenv(FONTSERVER) failed\n");
        return 17;
    }
    server = FSOpenServer(NULL);
    if (server != NULL) {
        fprintf(stderr, "FSOpenServer(NULL) must fail for an unreachable FONTSERVER\n");
        return 18;
    }
    (void)unsetenv("FONTSERVER");
    return 0;
}

int main(void)
{
    int status;

    status = check_fsservername();
    if (status != 0)
        return status;
    status = check_allocation();
    if (status != 0)
        return status;
    status = check_null_safe_destructors();
    if (status != 0)
        return status;
    status = check_fsopenserver_failure_contract();
    if (status != 0)
        return status;

    puts("LIBFS_TEST api_contract PASS");
    return 0;
}
