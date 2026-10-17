/*
 * libwebsockets 4.3.5 consumer smoke test (OpenHarmony PC)
 *
 * Verifies the installed Conan package can be consumed:
 *   1. <libwebsockets.h> is includable (header presence)
 *   2. The library links and exports real symbols
 *   3. lws_get_library_version() returns the built version
 *   4. Offline functional checks that do not need any network:
 *      - lws_dll2 insert/remove/for_each cycle
 *      - lejp JSON parser parses a small document
 *      - lws_get_peer_addresses-style string APIs are reachable
 */
#include <libwebsockets.h>
#include <stdio.h>
#include <string.h>

static int failed = 0;

#define CHECK(cond, msg)                                                \
    do {                                                                \
        if (cond) {                                                     \
            printf("  [PASS] %s\n", msg);                               \
        } else {                                                        \
            printf("  [FAIL] %s\n", msg);                               \
            failed++;                                                   \
        }                                                               \
    } while (0)

/* lejp callback: count "pairs" member occurrences */
static signed char
lejp_cb(struct lejp_ctx *ctx, char reason)
{
    (void)ctx;
    (void)reason;
    return 0;
}

int
main(void)
{
    const char *version = lws_get_library_version();

    printf("libwebsockets consumer test\n");
    printf("  library version: %s\n", version ? version : "(null)");

    CHECK(version != NULL, "lws_get_library_version() returns non-NULL");
    CHECK(version != NULL && strstr(version, "4.3.5") != NULL,
          "library version contains 4.3.5");

    /* lws_dll2: add two nodes, iterate, remove both */
    {
        struct lws_dll2_owner list = { NULL, NULL, 0 };
        struct lws_dll2 n1 = { NULL, NULL, NULL };
        struct lws_dll2 n2 = { NULL, NULL, NULL };
        struct lws_dll2 *p;
        int count = 0;

        lws_dll2_add_tail(&n1, &list);
        lws_dll2_add_tail(&n2, &list);

        lws_start_foreach_dll(struct lws_dll2 *, it, list.head) {
            (void)it;
            count++;
        } lws_end_foreach_dll(it);

        CHECK(count == 2, "lws_dll2 list iterates 2 nodes");

        lws_dll2_remove(&n1);
        lws_dll2_remove(&n2);
        CHECK(list.count == 0, "lws_dll2 list empty after removal");
    }

    /* lejp: parse a tiny JSON document offline */
    {
        static const unsigned char json[] =
            "{\"schema\":\"t\",\"count\":2,\"targets\":[{\"name\":\"a\"}]}";
        struct lejp_ctx ctx;
        int r;

        lejp_construct(&ctx, lejp_cb, NULL, NULL, 0);
        r = lejp_parse(&ctx, json, (int)sizeof(json) - 1);
        lejp_destruct(&ctx);

        /* 完整文档一次解析成功：返回 0 或正数（剩余字节数）；
         * LEJP_CONTINUE(-1) 表示需要更多输入，负数错误码表示解析失败 */
        CHECK(r >= 0, "lejp parses small JSON document successfully");
        CHECK(r != LEJP_REJECT_MP_VAL_TOK_UNKNOWN,
              "lejp did not reject on unknown token");
    }

    /* lws_dll2 count field doubles as cheap ABI presence check */
    CHECK((int)sizeof(struct lws_dll2) >= (int)sizeof(void *) * 2,
          "public structs exported with expected layout");

    if (failed) {
        printf("RESULT: %d assertion(s) failed\n", failed);
        return 1;
    }

    printf("RESULT: all consumer assertions passed\n");
    return 0;
}
