#include <fduserdata.h>

#include <stdio.h>
#include <string.h>

/* Consumer test for libfduserdata (R34: really exercises the library).
 * TAP-style output: each CHECK prints "ok N name" or "not ok N name".
 * The test_package conanfile counts the "ok" lines (14 checks total).
 */
static int g_n = 0;

#define CHECK(cond, name)                               \
    do {                                                \
        ++g_n;                                          \
        if (!(cond)) {                                  \
            printf("not ok %d %s\n", g_n, name);        \
            return 1;                                   \
        }                                               \
        printf("ok %d %s\n", g_n, name);                \
    } while (0)

struct mydata {
    int value;
    char tag[32];
};

static int g_cb_count = 0;

static void on_destroy(int fd, void *data, void *arg)
{
    (void) data;
    (void) arg;
    (void) fd;
    ++g_cb_count;
}

int main(void)
{
    /* Unbuffered TAP output: if the binary is killed (timeout/OOM) the
     * already-printed \"ok\" lines must survive in the log for diagnosis. */
    setvbuf(stdout, NULL, _IONBF, 0);

    /* T1: create a table with the default hash size. */
    FDUSERDATA *table = fduserdata_create(0);
    CHECK(table != NULL, "create-default");

    /* T2: new element on fd 10, put closes the critical section. */
    struct mydata *d10 = fduserdata_new(table, 10, struct mydata);
    CHECK(d10 != NULL, "new-fd10");
    d10->value = 100;
    (void) snprintf(d10->tag, sizeof(d10->tag), "ten");
    fduserdata_put(d10);
    CHECK(1, "put-fd10");

    /* T3: get fd 10 back and verify the payload. */
    struct mydata *g10 = fduserdata_get(table, 10);
    CHECK(g10 != NULL, "get-fd10");
    CHECK(g10->value == 100 && strcmp(g10->tag, "ten") == 0, "payload-fd10");
    fduserdata_put(g10);

    /* T4: colliding slot (10 & 63 == 74 & 63) coexists without overwrite.
     * NOTE: the table uses a single non-recursive mutex. new/get return
     * with the lock HELD; put/del release it. Two gets must never be held
     * at the same time (get(10) then get(74) without put deadlocks and the
     * watchdog kills the binary with SIGKILL). Verify coexistence with
     * sequential get/check/put pairs. */
    struct mydata *d74 = fduserdata_new(table, 74, struct mydata);
    CHECK(d74 != NULL, "new-fd74-collide");
    d74->value = 740;
    fduserdata_put(d74);
    g10 = fduserdata_get(table, 10);
    CHECK(g10 != NULL, "get-fd10-collide");
    CHECK(g10->value == 100, "payload-fd10-collide");
    fduserdata_put(g10);
    struct mydata *g74 = fduserdata_get(table, 74);
    CHECK(g74 != NULL, "get-fd74-collide");
    CHECK(g74->value == 740, "payload-fd74-collide");
    fduserdata_put(g74);

    /* T5: delete fd 10, then lookup must fail. */
    g10 = fduserdata_get(table, 10);
    CHECK(g10 != NULL, "get-before-del");
    CHECK(fduserdata_del(g10) == 0, "del-fd10");
    CHECK(fduserdata_get(table, 10) == NULL, "get-after-del-null");

    /* T6: destroy with callback visits remaining elements, then frees. */
    fduserdata_destroy_cb(table, on_destroy, NULL);
    CHECK(g_cb_count == 1, "destroy-cb-count");

    printf("libfduserdata consumer test passed\n");
    return 0;
}
