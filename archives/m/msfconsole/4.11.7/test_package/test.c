/*
 * test.c — msfconsole 4.11.7 test_package
 *
 * R34: This test actually invokes the package's binaries via system().
 * msfconsole is an application package — there is no library to link.
 * We call the installed C tools (time-key, stat-key) and verify their
 * expected behavior.
 */
#include <stdio.h>
#include <stdlib.h>

int main(void)
{
    int rc;

    /* time-key: no args → outputs hex time key, exits 0 */
    rc = system("time-key");
    if (rc != 0) {
        fprintf(stderr, "FAIL: time-key exited with code %d\n", rc);
        return 1;
    }

    /* stat-key: no args → usage error, exits 1 */
    rc = system("stat-key");
    if (rc == 0) {
        fprintf(stderr, "FAIL: stat-key should have failed with no args\n");
        return 1;
    }

    printf("msfconsole binary tests: OK\n");
    return 0;
}
