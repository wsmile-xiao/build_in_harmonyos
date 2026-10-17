/*
 * test_package — microrl-remaster 2.6.0 consumer test (HarmonyOS PC).
 *
 * Consumer-perspective verification: uses ONLY the installed public headers
 * (microrl/microrl.h) and the published static library. Feeds a real command
 * line into the public microrl_processing_input() API and asserts that the
 * execute callback fires with the expected tokens, and that
 * microrl_get_version() reports 2.6.0.
 */
#include <stdio.h>
#include <string.h>
#include <stdint.h>
#include <microrl/microrl.h>

/* Captured state from the execute callback */
static int g_exec_called = 0;
static int g_exec_argc = 0;
static char g_exec_argv0[32] = {0};

static int out_fn(struct microrl* mrl, const char* str)
{
    (void)mrl;
    (void)str;
    return 0;
}

static int exec_fn(struct microrl* mrl, int argc, const char* const* argv)
{
    (void)mrl;
    g_exec_called = 1;
    g_exec_argc = argc;
    if (argc > 0 && argv[0]) {
        snprintf(g_exec_argv0, sizeof(g_exec_argv0), "%s", argv[0]);
    }
    return 0;
}

int main(void)
{
    uint32_t ver = microrl_get_version();
    microrl_t mrl;
    int rc = 0;

    /* Version check: 2.6.0 -> 0x020600 */
    if (ver != 0x020600) {
        fprintf(stderr, "FAIL: microrl_get_version() = 0x%06x, expected 0x020600\n", ver);
        rc = 1;
    }

    if (microrl_init(&mrl, out_fn, exec_fn) != microrlOK) {
        fprintf(stderr, "FAIL: microrl_init()\n");
        return 1;
    }

    /* Feed "hello world\n" through the public input-processing API */
    const char* line = "hello world\n";
    microrlr_t r = microrl_processing_input(&mrl, line, strlen(line));
    if (r != microrlOK) {
        fprintf(stderr, "FAIL: microrl_processing_input() = %d\n", (int)r);
        rc = 1;
    }

    if (!g_exec_called) {
        fprintf(stderr, "FAIL: execute callback was not invoked\n");
        rc = 1;
    } else if (g_exec_argc != 2 || strcmp(g_exec_argv0, "hello") != 0) {
        fprintf(stderr, "FAIL: execute callback argc=%d argv0='%s', expected 2/'hello'\n",
                g_exec_argc, g_exec_argv0);
        rc = 1;
    }

    if (rc == 0) {
        printf("test microrl-remaster 2.6.0: OK (version 0x%06x, exec argc=%d argv0=%s)\n",
               ver, g_exec_argc, g_exec_argv0);
    }
    return rc;
}
