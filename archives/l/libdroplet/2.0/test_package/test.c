#include <stdio.h>
#include <string.h>
#include <droplet.h>
#include <droplet/converters.h>

/*
 * test_package consumer test — libdroplet 2.0
 *
 * Exercises real libdroplet public API (R34): library init,
 * status-string conversion, HTTP method / canned-ACL converters
 * and size formatting.  Returns non-zero on any failed assertion.
 */
static int failures = 0;
static int checks = 0;

#define CHECK(cond, msg)                                          \
    do {                                                          \
        checks++;                                                 \
        if (!(cond)) {                                            \
            fprintf(stderr, "FAIL: %s (line %d)\n", msg, __LINE__); \
            failures++;                                           \
        }                                                         \
    } while (0)

int main(void)
{
    /* 1. library lifecycle — dpl_init / dpl_free */
    dpl_status_t st = dpl_init();
    CHECK(st == DPL_SUCCESS, "dpl_init() returns DPL_SUCCESS");
    if (st == DPL_SUCCESS) {
        const char *s = dpl_status_str(DPL_SUCCESS);
        CHECK(s != NULL, "dpl_status_str(DPL_SUCCESS) non-NULL");
        CHECK(strcmp(s, "DPL_SUCCESS") == 0,
              "dpl_status_str(DPL_SUCCESS) == \"DPL_SUCCESS\"");
    }

    /* 2. converters — HTTP method string -> enum -> string round-trip */
    {
        char get[] = "GET";
        dpl_method_t m = dpl_method(get);
        CHECK(m == DPL_METHOD_GET, "dpl_method(\"GET\") == DPL_METHOD_GET");
        if (m == DPL_METHOD_GET) {
            char *ms = dpl_method_str(m);
            CHECK(ms != NULL && strcmp(ms, "GET") == 0,
                  "dpl_method_str round-trip == \"GET\"");
        }
    }

    /* 3. converters — canned ACL string -> enum -> string round-trip */
    {
        char priv[] = "private";
        dpl_canned_acl_t a = dpl_canned_acl(priv);
        CHECK(a == DPL_CANNED_ACL_PRIVATE, "dpl_canned_acl(\"private\") == DPL_CANNED_ACL_PRIVATE");
        if (a == DPL_CANNED_ACL_PRIVATE) {
            char *as = dpl_canned_acl_str(a);
            CHECK(as != NULL && strcmp(as, "private") == 0,
                  "dpl_canned_acl_str round-trip == \"private\"");
        }
    }

    /* 4. size formatter (1000 进制: 1024 -> "1 KB") */
    {
        char *sz = dpl_size_str(1024ULL);
        CHECK(sz != NULL, "dpl_size_str(1024) non-NULL");
        if (sz != NULL)
            CHECK(strstr(sz, "KB") != NULL,
                  "dpl_size_str(1024) uses 1000-based unit (KB)");
    }

    dpl_free();

    if (failures == 0) {
        printf("test_libdroplet: %d checks OK (4 groups)\n", checks);
        return 0;
    }
    fprintf(stderr, "test_libdroplet: %d/%d check(s) FAILED\n",
            failures, checks);
    return 1;
}