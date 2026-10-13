/* Consumer checks the exact bytes emitted by the installed public API.
 * Explicit status checks remain active in Release/NDEBUG builds. */
#define _POSIX_C_SOURCE 200809L
#include <subunit/child.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

int main(void)
{
    int pipefd[2] = {-1, -1}, saved = -1, rc = 1;
    char bytes[128];
    ssize_t length;
    const char expected[] = "test: consumer-smoke\nsuccess: consumer-smoke\n";
    if (fflush(stdout) || pipe(pipefd)) goto cleanup;
    saved = dup(STDOUT_FILENO);
    if (saved < 0 || dup2(pipefd[1], STDOUT_FILENO) < 0) goto cleanup;
    subunit_test_start("consumer-smoke");
    subunit_test_pass("consumer-smoke");
    if (fflush(stdout) || dup2(saved, STDOUT_FILENO) < 0) goto cleanup;
    if (close(pipefd[1])) { pipefd[1] = -1; goto cleanup; }
    pipefd[1] = -1;
    length = read(pipefd[0], bytes, sizeof(bytes));
    if (length != (ssize_t)(sizeof(expected)-1) || memcmp(bytes, expected, sizeof(expected)-1)) goto cleanup;
    rc = 0;
cleanup:
    if (saved >= 0) {
        if (dup2(saved, STDOUT_FILENO) < 0) rc = 1;
        if (close(saved)) rc = 1;
    }
    if (pipefd[0] >= 0 && close(pipefd[0])) rc = 1;
    if (pipefd[1] >= 0 && close(pipefd[1])) rc = 1;
    if (!rc) puts("CONSUMER_TEST_PASS=1/1");
    else fputs("FAIL: subunit protocol byte comparison\n", stderr);
    return rc;
}
