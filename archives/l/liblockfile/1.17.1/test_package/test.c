#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <lockfile.h>

int main(void) {
    const char *lockfile = "testlock.lock";
    int r;

    /* remove any stale lock from a previous run */
    unlink(lockfile);

    /* create the lock; must succeed on the first attempt */
    r = lockfile_create(lockfile, 1, L_PID);
    if (r != 0) {
        fprintf(stderr, "lockfile_create failed: rc=%d\n", r);
        return 1;
    }
    if (access(lockfile, F_OK) != 0) {
        fprintf(stderr, "lockfile missing after create\n");
        lockfile_remove(lockfile);
        return 1;
    }

    /* a second lock attempt while the lock is held must fail */
    r = lockfile_create(lockfile, 1, L_PID);
    if (r == 0) {
        fprintf(stderr, "double lock unexpectedly succeeded\n");
        lockfile_remove(lockfile);
        return 1;
    }

    /* check reports the lock as valid (held by our own live pid) */
    if (lockfile_check(lockfile, L_PID) != 0) {
        fprintf(stderr, "lockfile_check failed for held lock\n");
        lockfile_remove(lockfile);
        return 1;
    }

    /* remove the lock and verify it is gone */
    if (lockfile_remove(lockfile) != 0) {
        fprintf(stderr, "lockfile_remove failed\n");
        return 1;
    }
    if (access(lockfile, F_OK) == 0) {
        fprintf(stderr, "lockfile still exists after remove\n");
        return 1;
    }

    printf("test liblockfile 1.17.1: OK\n");
    return 0;
}
