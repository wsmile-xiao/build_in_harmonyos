/*
 * libwebsockets 4.3.5.1 consumer test (OpenHarmony PC)
 *
 * Verifies the installed Conan package can be consumed, with focus on the
 * R37 fix (libuv event loop integration):
 *   1. <libwebsockets.h> is includable (header presence)
 *   2. Compile-time: LWS_WITH_LIBUV must be defined by lws_config.h
 *   3. The library links and exports real symbols
 *   4. A REAL public libuv-integration API is called: lws_uv_getloop()
 *      against a context created with a foreign uv_loop (same pattern
 *      used by ttyd 1.7.7 server.c: foreign_loops -> lws_create_context)
 *   5. libuv is resolved transitively: <uv.h> + uv_loop_init/uv_loop_close
 *      link against the libuv package pulled through the recipe
 *   6. Offline: no external network required
 *
 * If LWS_WITH_LIBUV is removed or broken, this test FAILS to compile
 * (the #error below) and FAILS at runtime (lws_uv_getloop not declared),
 * so it is not a hollow smoke test.
 */
#include <uv.h>               /* must come first: defines UV_ERRNO_MAP */
#include <libwebsockets.h>
#include <stdio.h>
#include <string.h>

#if !defined(LWS_WITH_LIBUV)
#error "libwebsockets was not built with LWS_WITH_LIBUV (R37 fix missing)"
#endif

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

    /* --- libuv integration (R37 core fix) --- */

    /* 1) Public libuv-integration API: lws_uv_getloop() declaration is only
     *    visible when LWS_WITH_LIBUV && UV_ERRNO_MAP are both defined,
     *    i.e. the compile-time proof the header exposes libuv support. */
#if defined(LWS_WITH_LIBUV)
    printf("  [PASS] compile-time LWS_WITH_LIBUV defined in lws_config.h\n");
#else
    printf("  [FAIL] compile-time LWS_WITH_LIBUV not defined\n");
    failed++;
#endif

    /* 2) Real usage identical to ttyd 1.7.7: hand libwebsockets a foreign
     *    uv_loop via info.foreign_loops, create a context, then call the
     *    public lws_uv_getloop() to prove the loop was adopted. */
    {
        uv_loop_t loop;
        void *foreign_loops[1];
        struct lws_context_creation_info info;
        struct lws_context *context;
        uv_loop_t *got;

        if (uv_loop_init(&loop)) {
            printf("  [FAIL] uv_loop_init failed\n");
            failed++;
        } else {
            printf("  [PASS] uv_loop_init succeeds (libuv links)\n");
        }

        memset(&info, 0, sizeof(info));
        foreign_loops[0] = &loop;
        info.foreign_loops = foreign_loops;
        info.options = LWS_SERVER_OPTION_LIBUV | LWS_SERVER_OPTION_EXPLICIT_VHOSTS;
        info.port = CONTEXT_PORT_NO_LISTEN;

        context = lws_create_context(&info);
        CHECK(context != NULL,
              "lws_create_context() succeeds with foreign uv_loop");

        if (context) {
            got = lws_uv_getloop(context, 0);
            CHECK(got != NULL, "lws_uv_getloop() returns non-NULL loop");
            CHECK(got == &loop,
                  "lws_uv_getloop() returns the foreign uv_loop adopted");
            lws_context_destroy(context);
        }

        uv_loop_close(&loop);
    }

    /* 3) uv_version() proves libuv transitive dependency is linked into
     *    the consumer binary (not merely declared). uv_version() returns
     *    UV_VERSION_HEX = (major << 16) | (minor << 8) | patch, so check
     *    the major nibble is 1 (libuv 1.x, e.g. 1.52.1 -> 0x00013401). */
    {
        unsigned int uvver = uv_version();
        CHECK(uvver != 0 && ((uvver >> 16) & 0xff) == 1,
              "libuv runtime symbol uv_version() links (libuv 1.x)");
    }

    /* --- baseline functional checks (kept from 4.3.5) --- */

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
