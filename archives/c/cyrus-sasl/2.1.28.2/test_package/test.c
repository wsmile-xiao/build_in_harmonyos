/* cyrus-sasl test_package —— 真实 API 断言（非 dlopen 空壳）
 * 证明：① 版本正确 ② sasl_client_init 成功 ③ 机制插件被 dlopen 加载并可用
 * 提供 authname/password 回调后 listmech 才会枚举需要凭据的机制（PLAIN/SCRAM/...）；
 * 硬断言 PLAIN + SCRAM 均加载（SCRAM 顺带证明 libcrypto 运行期可解析）。 */
#include <sasl/sasl.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static int cb_getsimple(void *ctx, int id, const char **result, unsigned *len) {
    (void)ctx; (void)id;
    *result = "testuser";
    if (len) *len = 8;
    return SASL_OK;
}
static int cb_getsecret(sasl_conn_t *conn, void *ctx, int id, sasl_secret_t **psecret) {
    (void)conn; (void)ctx; (void)id;
    static sasl_secret_t *s = NULL;
    const char *pw = "testpass";
    size_t n = strlen(pw);
    if (!s) {
        s = (sasl_secret_t *)malloc(sizeof(sasl_secret_t) + n);
        if (!s) return SASL_NOMEM;
    }
    s->len = (unsigned)n;
    memcpy(s->data, pw, n);
    *psecret = s;
    return SASL_OK;
}

int main(void) {
    const char *impl = NULL;
    int major = 0, minor = 0, step = 0, patch = 0;
    sasl_version_info(&impl, NULL, &major, &minor, &step, &patch);
    printf("cyrus-sasl impl=%s version=%d.%d.%d.%d\n",
           impl ? impl : "?", major, minor, step, patch);
    if (major != 2 || minor != 1) {
        fprintf(stderr, "FAIL: unexpected version (want 2.1.x)\n");
        return 1;
    }

#ifdef SASL_PLUGIN_DIR
    if (sasl_set_path(SASL_PATH_TYPE_PLUGIN, (char *)SASL_PLUGIN_DIR) != SASL_OK) {
        fprintf(stderr, "FAIL: sasl_set_path(%s) failed\n", SASL_PLUGIN_DIR);
        return 1;
    }
    printf("plugin dir = %s\n", SASL_PLUGIN_DIR);
#endif

    sasl_callback_t callbacks[] = {
        { SASL_CB_AUTHNAME, (int (*)(void))&cb_getsimple, NULL },
        { SASL_CB_USER,     (int (*)(void))&cb_getsimple, NULL },
        { SASL_CB_PASS,     (int (*)(void))&cb_getsecret, NULL },
        { SASL_CB_LIST_END, NULL, NULL }
    };

    int r = sasl_client_init(callbacks);
    if (r != SASL_OK) {
        fprintf(stderr, "FAIL: sasl_client_init = %d\n", r);
        return 1;
    }

    sasl_conn_t *conn = NULL;
    r = sasl_client_new("smtp", "localhost", NULL, NULL, callbacks, 0, &conn);
    if (r != SASL_OK) {
        fprintf(stderr, "FAIL: sasl_client_new = %d\n", r);
        return 1;
    }

    const char *mechlist = NULL;
    unsigned len = 0;
    int count = 0;
    r = sasl_listmech(conn, NULL, "", " ", "", &mechlist, &len, &count);
    if (r != SASL_OK) {
        fprintf(stderr, "FAIL: sasl_listmech = %d\n", r);
        return 1;
    }
    printf("client mechs (%d): %s\n", count, mechlist ? mechlist : "(none)");

    /* 硬断言：PLAIN（无外部依赖插件）+ SCRAM（需 libcrypto 运行期解析）均已加载可用 */
    if (!mechlist || !strstr(mechlist, "PLAIN")) {
        fprintf(stderr, "FAIL: PLAIN plugin not loaded\n");
        return 1;
    }
    if (!strstr(mechlist, "SCRAM-SHA-256")) {
        fprintf(stderr, "FAIL: SCRAM plugin not loaded (libcrypto runtime link broken?)\n");
        return 1;
    }

    sasl_dispose(&conn);
    sasl_client_done();
    printf("cyrus-sasl test PASS\n");
    return 0;
}
