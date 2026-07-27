#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <nspr.h>
#include <prthread.h>
#include <prtime.h>
#include <prinit.h>
#include <prlock.h>
#include <prmem.h>
#include <prio.h>
#include <pratom.h>
#include <prinrval.h>
#include <prlog.h>

/* Thread test: shared counter protected by lock */
static PRLock *g_lock = NULL;
static PRInt32 g_counter = 0;

static void PR_CALLBACK thread_func(void *arg)
{
    PR_Lock(g_lock);
    g_counter++;
    PR_Unlock(g_lock);
}

/* I/O test: write to / then read from a temp file */
static int test_file_io(void)
{
    PRFileDesc *fd;
    char buf[64];
    const char *msg = "NSPR test";
    PRInt32 n;

    fd = PR_Open("/data/storage/el2/base/cache/nspr-test.tmp",
                 PR_CREATE_FILE | PR_WRONLY | PR_TRUNCATE, 0644);
    if (!fd) {
        printf("PR_Open (write): FAILED\n");
        return 1;
    }
    n = PR_Write(fd, msg, (PRInt32)strlen(msg));
    PR_Close(fd);
    if (n != (PRInt32)strlen(msg)) {
        printf("PR_Write: FAILED (wrote %d bytes)\n", (int)n);
        return 1;
    }
    printf("PR_Write: OK (%d bytes)\n", (int)n);

    fd = PR_Open("/data/storage/el2/base/cache/nspr-test.tmp",
                 PR_RDONLY, 0);
    if (!fd) {
        printf("PR_Open (read): FAILED\n");
        return 1;
    }
    memset(buf, 0, sizeof(buf));
    n = PR_Read(fd, buf, sizeof(buf) - 1);
    PR_Close(fd);
    if (n != (PRInt32)strlen(msg) || strcmp(buf, msg) != 0) {
        printf("PR_Read: FAILED (got '%s')\n", buf);
        return 1;
    }
    printf("PR_Read: OK ('%s')\n", buf);

    /* Cleanup */
    PR_Delete("/data/storage/el2/base/cache/nspr-test.tmp");
    return 0;
}

int main(void)
{
    int failures = 0;

    const char *ver = PR_GetVersion();
    printf("NSPR version: %s\n", ver ? ver : "unknown");

    /* Verify PR_Init / PR_Cleanup work */
    PR_Init(PR_USER_THREAD, PR_PRIORITY_NORMAL, 0);
    printf("PR_Init: OK\n");

    /* Verify PR_GetVersion works */
    printf("PR_GetVersion: %s\n", ver ? ver : "null");
    if (!ver) failures++;

    /* Verify time functions */
    PRTime now = PR_Now();
    printf("PR_Now: %lld\n", (long long)now);
    if (now <= 0) failures++;

    /* Verify interval timing */
    PRIntervalTime ticks = PR_IntervalNow();
    PRIntervalTime ms = PR_MillisecondsToInterval(100);
    printf("PR_IntervalNow: %u, PR_MillisecondsToInterval(100): %u\n",
           (unsigned)ticks, (unsigned)ms);
    if (ms == 0) failures++;

    /* Verify atomic operations */
    PRInt32 atom = 0;
    PRInt32 old = PR_AtomicIncrement(&atom);
    printf("PR_AtomicIncrement: %d -> %d\n", (int)old - 1, (int)old);
    if (old != 1) failures++;
    old = PR_AtomicDecrement(&atom);
    printf("PR_AtomicDecrement: %d -> %d\n", (int)old + 1, (int)old);
    if (old != 0) failures++;

    /* Verify memory allocation */
    char *mem = (char *)PR_Malloc(128);
    if (!mem) {
        printf("PR_Malloc: FAILED\n");
        failures++;
    } else {
        memset(mem, 0xAB, 128);
        PR_Free(mem);
        printf("PR_Malloc/PR_Free: OK\n");
    }

    /* Verify lock operations */
    g_lock = PR_NewLock();
    if (!g_lock) {
        printf("PR_NewLock: FAILED\n");
        failures++;
    } else {
        PR_Lock(g_lock);
        PR_Unlock(g_lock);
        printf("PR_NewLock/Lock/Unlock: OK\n");
    }

    /* Verify thread creation and joining (requires g_lock) */
    if (g_lock) {
        g_counter = 0;
        PRThread *t1 = PR_CreateThread(PR_USER_THREAD, thread_func, NULL,
                                       PR_PRIORITY_NORMAL, PR_LOCAL_THREAD,
                                       PR_JOINABLE_THREAD, 0);
        PRThread *t2 = PR_CreateThread(PR_USER_THREAD, thread_func, NULL,
                                       PR_PRIORITY_NORMAL, PR_LOCAL_THREAD,
                                       PR_JOINABLE_THREAD, 0);
        if (!t1 || !t2) {
            printf("PR_CreateThread: FAILED\n");
            failures++;
        } else {
            PR_JoinThread(t1);
            PR_JoinThread(t2);
            printf("PR_JoinThread: OK (counter=%d, expected 2)\n", (int)g_counter);
            if (g_counter != 2) failures++;
        }
        PR_DestroyLock(g_lock);
    } else {
        printf("PR_CreateThread/JoinThread: SKIPPED (g_lock not available)\n");
    }

    /* Verify file I/O */
    failures += test_file_io();

    /* Verify PR_GetEnv / PR_SetEnv */
    PR_SetEnv("NSPR_TEST=hello");
    const char *env = PR_GetEnv("NSPR_TEST");
    printf("PR_SetEnv/PR_GetEnv: %s\n", env ? env : "null");
    if (!env || strcmp(env, "hello") != 0) failures++;

    /* Verify logging */
    PR_LogPrint("NSPR logging test: %s", "OK");
    printf("PR_LogPrint: OK\n");

    PR_Cleanup();
    printf("PR_Cleanup: OK\n");

    if (failures == 0) {
        printf("All NSPR API tests passed.\n");
    } else {
        printf("FAILURES: %d test(s) failed.\n", failures);
    }
    return failures;
}