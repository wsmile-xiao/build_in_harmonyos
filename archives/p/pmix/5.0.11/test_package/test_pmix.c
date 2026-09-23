/* test_pmix.c — PMIx 5.0.11 consumer test (R34 substantive).
 *
 * End-to-end API verification using the upstream "simptest" pattern:
 * the test process acts as a PMIx server (PMIx_server_init +
 * PMIx_server_setup_fork), forks a child client which connects back
 * through the server-provided environment and runs PMIx_Init ->
 * PMIx_Finalize. This exercises the real client/server wire protocol
 * (PTL + BFROPS + GDS MCA components), not just symbol resolution.
 *
 * Assertions are printed as "ASSERT <n> <OK|FAIL>: ..." lines and
 * summarized in "PMIX_TEST_ASSERTIONS: total=N passed=N".
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>

#include <pmix.h>
#include <pmix_server.h>

static int g_total = 0;
static int g_passed = 0;

static void check(int cond, const char *desc)
{
    g_total++;
    if (cond) {
        g_passed++;
        printf("ASSERT %d OK: %s\n", g_total, desc);
    } else {
        printf("ASSERT %d FAIL: %s\n", g_total, desc);
    }
    fflush(stdout);
}

int main(void)
{
    pmix_proc_t proc;
    int rc;

    /* 1-2: version sanity */
    const char *ver = PMIx_Get_version();
    check(ver != NULL, "PMIx_Get_version() returns non-NULL");
    check(ver != NULL && strstr(ver, "5.0.11") != NULL,
          "PMIx_Get_version() contains \"5.0.11\"");

    /* 3: server side init */
    rc = PMIx_server_init(NULL, NULL, 0);
    check(rc == PMIX_SUCCESS, "PMIx_server_init() == PMIX_SUCCESS");

    if (rc != PMIX_SUCCESS) {
        printf("PMIX_TEST_ASSERTIONS: total=%d passed=%d\n", g_total, g_passed);
        return 1;
    }

    /* register the client that will fork+connect */
    memset(&proc, 0, sizeof(proc));
    strncpy(proc.nspace, "testns", PMIX_MAX_NSLEN - 1);
    proc.rank = 0;
    PMIx_server_register_client(&proc, getuid(), getgid(), NULL, NULL, NULL);

    /* 4: prepare the fork environment (PMIX_SERVER_URI + security creds) */
    char **child_env = NULL;
    rc = PMIx_server_setup_fork(&proc, &child_env);
    check(rc == PMIX_SUCCESS, "PMIx_server_setup_fork() == PMIX_SUCCESS");

    if (rc != PMIX_SUCCESS) {
        PMIx_server_finalize();
        printf("PMIX_TEST_ASSERTIONS: total=%d passed=%d\n", g_total, g_passed);
        return 1;
    }

    fflush(stdout);
    pid_t pid = fork();
    if (pid == 0) {
        /* child: apply server-provided env and run the client handshake */
        for (char **e = child_env; e && *e; e++) {
            putenv(strdup(*e));
        }
        pmix_proc_t myproc;
        memset(&myproc, 0, sizeof(myproc));
        int crc = PMIx_Init(&myproc, NULL, 0);
        if (crc != PMIX_SUCCESS) {
            printf("ASSERT FAIL(client): PMIx_Init rc=%d\n", crc);
            _exit(1);
        }
        if (myproc.nspace[0] == '\0' || myproc.rank < 0) {
            printf("ASSERT FAIL(client): bad nspace/rank\n");
            _exit(2);
        }
        printf("ASSERT OK(client): PMIx_Init PMIX_SUCCESS, nspace='%s', rank=%d\n",
               myproc.nspace, (int)myproc.rank);
        int frc = PMIx_Finalize(NULL, 0);
        if (frc != PMIX_SUCCESS) {
            printf("ASSERT FAIL(client): PMIx_Finalize rc=%d\n", frc);
            _exit(3);
        }
        printf("ASSERT OK(client): PMIx_Finalize PMIX_SUCCESS\n");
        fflush(stdout);
        _exit(0);
    }

    int status = 0;
    waitpid(pid, &status, 0);

    /* 5-7: client handshake results (relayed through the exit code) */
    check(WIFEXITED(status) && WEXITSTATUS(status) == 0,
          "client PMIx_Init() == PMIX_SUCCESS");
    check(WIFEXITED(status) && WEXITSTATUS(status) != 2,
          "client nspace non-empty and rank valid");
    check(WIFEXITED(status) && WEXITSTATUS(status) != 3,
          "client PMIx_Finalize() == PMIX_SUCCESS");

    /* 8: server teardown */
    rc = PMIx_server_finalize();
    check(rc == PMIX_SUCCESS, "PMIx_server_finalize() == PMIX_SUCCESS");

    printf("PMIX_TEST_ASSERTIONS: total=%d passed=%d\n", g_total, g_passed);
    return (g_total == g_passed) ? 0 : 1;
}
