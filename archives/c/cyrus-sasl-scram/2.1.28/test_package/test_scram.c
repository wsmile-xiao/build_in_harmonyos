/* cyrus-sasl-scram 2.1.28 — 消费者测试（真实调用 libsasl2.a 里的 SCRAM 机制）。
 *
 * 与 dev 包内自带的 utils/testsuite 不同，本文件是**消费者视角**验证：
 * 用 CMakeDeps 生成的 cyrus-sasl-scram-config.cmake 找到 libsasl2.a，
 * 链接后在本进程内驱动 SCRAM 机制，检查
 *   - 版本、client/server 初始化与连接构造
 *   - client/server 两侧机制枚举都含 SCRAM 家族（5 个变体）
 *   - OHOS 特有点：SASL_PATH 指向不存在目录时机制依然可用（静态链入
 *     libsasl2.a，无运行期插件目录 / dlopen）
 *   - sasl_client_start() 真的产出 RFC 5802 client-first-message
 *     （gs2-header + n=<user>,r=<nonce>），而不是空壳/stub
 *   - 尽力而为：把 client-first 交给 sasl_server_start()，记录服务端
 *     是否要求口令后端（本包 --with-dblib=none，无 auxprop 口令库）
 *
 * 每个通过的检查打印恰好一行 "CHECK-OK: <name>"；conanfile.py 按行数统计。
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <sasl/sasl.h>

#define AUTHID   "scramuser"
#define PASSWORD "s3cr3t-password"

static const char *SCRAM_MECHS[] = {
    "SCRAM-SHA-1", "SCRAM-SHA-224", "SCRAM-SHA-256",
    "SCRAM-SHA-384", "SCRAM-SHA-512", NULL
};

/* ───────────────────────── SASL callbacks ───────────────────────── */

static int cb_getsimple(void *ctx, int id, const char **result, unsigned *len)
{
    (void) ctx;
    (void) id;
    *result = AUTHID;
    if (len) {
        *len = (unsigned) strlen(AUTHID);
    }
    return SASL_OK;
}

static int cb_getsecret(sasl_conn_t *conn, void *ctx, int id,
                        sasl_secret_t **psecret)
{
    static sasl_secret_t *secret = NULL;
    size_t n;
    (void) conn;
    (void) ctx;
    (void) id;

    n = strlen(PASSWORD);
    if (!secret) {
        secret = (sasl_secret_t *) malloc(sizeof(sasl_secret_t) + n);
        if (!secret) {
            return SASL_NOMEM;
        }
    }
    secret->len = (unsigned) n;
    memcpy(secret->data, PASSWORD, n);
    *psecret = secret;
    return SASL_OK;
}

static sasl_callback_t client_callbacks[] = {
    { SASL_CB_AUTHNAME, (int (*)(void)) &cb_getsimple, NULL },
    { SASL_CB_USER, (int (*)(void)) &cb_getsimple, NULL },
    { SASL_CB_PASS, (int (*)(void)) &cb_getsecret, NULL },
    { SASL_CB_LIST_END, NULL, NULL }
};

static sasl_callback_t server_callbacks[] = {
    { SASL_CB_LIST_END, NULL, NULL }
};

static int failed(const char *what, int rc)
{
    fprintf(stderr, "FAIL: %s (sasl rc=%d)\n", what, rc);
    return 1;
}

/* ─────────────────────── OHOS 特有点（静态链接） ─────────────────────── */

static int check_ohos_static_only(void)
{
    const char *sasl_path = getenv("SASL_PATH");
    sasl_conn_t *conn = NULL;
    const char *mechlist = NULL;
    unsigned mechlen = 0;
    int count = 0;
    int i;
    int r;

    /* OHOS 适配把 SCRAM 链进 libsasl2.a（--enable-scram + 静态构建），
     * 因此即使完全没有插件目录，机制也必须可用。 */
    printf("ohos-static probe: SASL_PATH=%s\n",
           sasl_path ? sasl_path : "(unset)");
    r = sasl_client_init(client_callbacks);
    if (r != SASL_OK) {
        return failed("sasl_client_init (ohos-static)", r);
    }
    r = sasl_client_new("smtp", "localhost", NULL, NULL, client_callbacks,
                        0, &conn);
    if (r != SASL_OK || conn == NULL) {
        return failed("sasl_client_new (ohos-static)", r);
    }
    r = sasl_listmech(conn, NULL, "", " ", "", &mechlist, &mechlen, &count);
    if (r != SASL_OK) {
        sasl_dispose(&conn);
        return failed("sasl_listmech (ohos-static)", r);
    }
    printf("ohos-static client mechs (%d): %s\n", count,
           mechlist ? mechlist : "(none)");
    for (i = 0; SCRAM_MECHS[i]; i++) {
        if (!mechlist || strstr(mechlist, SCRAM_MECHS[i]) == NULL) {
            sasl_dispose(&conn);
            fprintf(stderr, "FAIL: %s not statically registered "
                            "(SASL_PATH=%s)\n", SCRAM_MECHS[i],
                    sasl_path ? sasl_path : "(unset)");
            return 1;
        }
    }
    sasl_dispose(&conn);
    sasl_client_done();
    printf("CHECK-OK: ohos-static-scram-no-saslpath\n");
    return 0;
}

/* ───────────────────────── SCRAM 机制实际执行 ───────────────────────── */

/* RFC 5802 client-first-message = gs2-header client-first-bare
 *   gs2-header        = gs2-cbind-flag "," [ "a=" authzid ] ","
 *   client-first-bare = "n=" saslname "," "r=" c-nonce ["," extensions]
 * gs2-cbind-flag 为 "n"（客户端不支持 channel binding）；authzid 段可选，
 * 本测试的客户端回调同时提供 SASL_CB_USER，因此实际产出
 * "n,a=scramuser,n=scramuser,r=<nonce>" —— 合法形态，不能要求 "n,,"。
 */
static char g_client_first[1024];

static int check_scram_client_first(sasl_conn_t *cconn)
{
    const char *clientout = NULL;
    unsigned clientoutlen = 0;
    const char *mech = NULL;
    const char *sep;
    const char *nonce;
    int r;

    r = sasl_client_start(cconn, "SCRAM-SHA-1", NULL, &clientout,
                          &clientoutlen, &mech);
    if (r != SASL_CONTINUE && r != SASL_OK) {
        return failed("sasl_client_start(SCRAM-SHA-1)", r);
    }
    if (clientout == NULL || clientoutlen == 0) {
        fprintf(stderr, "FAIL: empty SCRAM-SHA-1 client-first message\n");
        return 1;
    }
    if (clientoutlen >= sizeof(g_client_first)) {
        fprintf(stderr, "FAIL: client-first message too long (%u)\n",
                clientoutlen);
        return 1;
    }
    memcpy(g_client_first, clientout, clientoutlen);
    g_client_first[clientoutlen] = '\0';
    printf("client-first: %s\n", g_client_first);

    if (strcmp(mech, "SCRAM-SHA-1") != 0) {
        fprintf(stderr, "FAIL: chosen mechanism is %s, want SCRAM-SHA-1\n",
                mech);
        return 1;
    }
    /* gs2-cbind-flag: "n" (client does not support channel binding) */
    if (strncmp(g_client_first, "n,", 2) != 0) {
        fprintf(stderr, "FAIL: gs2-cbind-flag is not \"n\": %s\n",
                g_client_first);
        return 1;
    }
    if (strstr(g_client_first, "n=" AUTHID) == NULL) {
        fprintf(stderr, "FAIL: client-first-bare lacks n=%s: %s\n",
                AUTHID, g_client_first);
        return 1;
    }
    sep = strstr(g_client_first, ",r=");
    if (sep == NULL) {
        fprintf(stderr, "FAIL: client-first-bare lacks r=<nonce>: %s\n",
                g_client_first);
        return 1;
    }
    nonce = sep + 3;
    if (strlen(nonce) < 16) {
        fprintf(stderr, "FAIL: SCRAM nonce too short (%u bytes): %s\n",
                (unsigned) strlen(nonce), nonce);
        return 1;
    }
    printf("CHECK-OK: scram-sha1-client-first-rfc5802\n");
    return 0;
}

/* 尽力而为：服务端处理 client-first。本包 --with-dblib=none，
 * 没有 auxprop 口令后端，服务端会要求数据库（SASL_NOUSER）；这里只
 * 记录服务端真实行为，不做通过/失败判定（口令后端不在本包范围内）。 */
static void probe_scram_server_first(const char *client_first)
{
    sasl_conn_t *sconn = NULL;
    const char *serverout = NULL;
    unsigned serveroutlen = 0;
    int r;

    r = sasl_server_new("smtp", "localhost", NULL, NULL, NULL, NULL, 0,
                        &sconn);
    if (r != SASL_OK || sconn == NULL) {
        printf("INFO: sasl_server_new rc=%d\n", r);
        return;
    }
    r = sasl_server_start(sconn, "SCRAM-SHA-1", client_first,
                          (unsigned) strlen(client_first), &serverout,
                          &serveroutlen);
    if (r == SASL_CONTINUE && serverout && serveroutlen) {
        printf("INFO: server-first (r=/s=/i=): %.*s\n",
               (int) serveroutlen, serverout);
    } else {
        printf("INFO: sasl_server_start rc=%d (%s) — 本包 --with-dblib=none，"
               "无 auxprop 口令库，服务端凭据验证需独立口令后端包\n",
               r, sasl_errstring(r, NULL, NULL));
    }
    sasl_dispose(&sconn);
}

int main(int argc, char **argv)
{
    const char *impl = NULL;
    const char *ver = NULL;
    int major = 0, minor = 0, step = 0, patch = 0;
    sasl_conn_t *cconn = NULL;
    sasl_conn_t *sconn = NULL;
    const char *mechlist = NULL;
    unsigned mechlen = 0;
    int count = 0;
    int i;
    int r;

    if (argc > 1 && strcmp(argv[1], "--ohos-static-only") == 0) {
        return check_ohos_static_only();
    }

    sasl_version_info(&impl, &ver, &major, &minor, &step, &patch);
    printf("libsasl2: impl=%s version=%s %d.%d.%d.%d\n", impl, ver,
           major, minor, step, patch);
    if (major != 2 || minor != 1) {
        fprintf(stderr, "FAIL: unexpected SASL version %d.%d\n", major, minor);
        return 1;
    }
    printf("CHECK-OK: version-2.1\n");

    r = sasl_client_init(client_callbacks);
    if (r != SASL_OK) {
        return failed("sasl_client_init", r);
    }
    printf("CHECK-OK: client-init\n");

    r = sasl_server_init(server_callbacks, "scram-consumer-test");
    if (r != SASL_OK) {
        return failed("sasl_server_init", r);
    }
    printf("CHECK-OK: server-init\n");

    r = sasl_client_new("smtp", "localhost", NULL, NULL, client_callbacks, 0,
                        &cconn);
    if (r != SASL_OK || cconn == NULL) {
        return failed("sasl_client_new", r);
    }
    printf("CHECK-OK: client-new\n");

    r = sasl_server_new("smtp", "localhost", NULL, NULL, NULL, NULL, 0,
                        &sconn);
    if (r != SASL_OK || sconn == NULL) {
        return failed("sasl_server_new", r);
    }
    printf("CHECK-OK: server-new\n");

    r = sasl_listmech(cconn, NULL, "", " ", "", &mechlist, &mechlen, &count);
    if (r != SASL_OK) {
        return failed("client sasl_listmech", r);
    }
    printf("client mechs (%d): %s\n", count, mechlist ? mechlist : "(none)");
    for (i = 0; SCRAM_MECHS[i]; i++) {
        if (!mechlist || strstr(mechlist, SCRAM_MECHS[i]) == NULL) {
            fprintf(stderr, "FAIL: client mechlist lacks %s: %s\n",
                    SCRAM_MECHS[i], mechlist ? mechlist : "(none)");
            return 1;
        }
    }
    printf("CHECK-OK: client-listmech-scram-family\n");

    r = sasl_listmech(sconn, NULL, "", " ", "", &mechlist, &mechlen, &count);
    if (r != SASL_OK) {
        return failed("server sasl_listmech", r);
    }
    printf("server mechs (%d): %s\n", count, mechlist ? mechlist : "(none)");
    for (i = 0; SCRAM_MECHS[i]; i++) {
        if (!mechlist || strstr(mechlist, SCRAM_MECHS[i]) == NULL) {
            fprintf(stderr, "FAIL: server mechlist lacks %s: %s\n",
                    SCRAM_MECHS[i], mechlist ? mechlist : "(none)");
            return 1;
        }
    }
    printf("CHECK-OK: server-listmech-scram-family\n");

    if (check_scram_client_first(cconn) != 0) {
        return 1;
    }
    probe_scram_server_first(g_client_first);

    sasl_dispose(&cconn);
    sasl_dispose(&sconn);
    sasl_client_done();
    sasl_server_done();
    printf("ALL CHECKS PASSED\n");
    return 0;
}
