/* test_msquic.c — libmsquic 2.5.7 L1 consumer test (R34).
 * Calls the real MsQuic API: MsQuicOpen2/MsQuicClose plus
 * RegistrationOpen/RegistrationClose. No network traffic.
 * Usage: ./test_msquic open | ./test_msquic registration | ./test_msquic all
 * Prints HMBS_TEST_PACKAGE_RESULT JSON on the "all" path.
 */
#include <stdio.h>
#include <string.h>
#include "msquic.h"

static int test_open(void) {
    const QUIC_API_TABLE* api = NULL;
    QUIC_STATUS s = MsQuicOpen2(&api);
    if (QUIC_FAILED(s) || api == NULL) {
        fprintf(stderr, "MsQuicOpen2 failed: 0x%x\n", (unsigned)s);
        return 1;
    }
    if (api->RegistrationOpen == NULL || api->RegistrationClose == NULL ||
        api->ConnectionOpen == NULL || api->StreamOpen == NULL) {
        fprintf(stderr, "API table missing function pointers\n");
        MsQuicClose(api);
        return 1;
    }
    printf("TEST open PASSED: MsQuicOpen2 ok, api=%p\n", (const void*)api);
    MsQuicClose(api);
    return 0;
}

static int test_registration(void) {
    const QUIC_API_TABLE* api = NULL;
    HQUIC reg = NULL;
    QUIC_STATUS s = MsQuicOpen2(&api);
    if (QUIC_FAILED(s) || api == NULL) {
        fprintf(stderr, "MsQuicOpen2 failed: 0x%x\n", (unsigned)s);
        return 1;
    }
    QUIC_REGISTRATION_CONFIG cfg;
    memset(&cfg, 0, sizeof(cfg));
    cfg.AppName = "hmbs-test";
    cfg.ExecutionProfile = QUIC_EXECUTION_PROFILE_LOW_LATENCY;
    s = api->RegistrationOpen(&cfg, &reg);
    if (QUIC_FAILED(s) || reg == NULL) {
        fprintf(stderr, "RegistrationOpen failed: 0x%x\n", (unsigned)s);
        MsQuicClose(api);
        return 1;
    }
    printf("TEST registration PASSED: RegistrationOpen ok, reg=%p\n", (void*)reg);
    api->RegistrationClose(reg);
    MsQuicClose(api);
    return 0;
}

int main(int argc, char** argv) {
    const char* mode = argc > 1 ? argv[1] : "all";
    if (strcmp(mode, "open") == 0) {
        return test_open();
    }
    if (strcmp(mode, "registration") == 0) {
        return test_registration();
    }
    /* all: run both cases, count, emit machine evidence */
    int passed = 0;
    int discovered = 2;
    printf("[1/2] MsQuicOpen2/Close...\n");
    if (test_open() == 0) { passed++; } else { printf("TEST open FAILED\n"); }
    printf("[2/2] RegistrationOpen/Close...\n");
    if (test_registration() == 0) { passed++; } else { printf("TEST registration FAILED\n"); }
    printf("test_msquic: %d/%d passed\n", passed, discovered);
    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,\"command\":\"./test_msquic all\",\"discovered\":%d,\"passedCount\":%d}\n",
        passed == discovered ? "true" : "false", discovered, passed);
    return passed == discovered ? 0 : 1;
}
