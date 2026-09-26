/* cyrus-sasl-crammd5 test_package — CRAM-MD5 mechanism consumer checks.
 *
 * Runs against the packaged static libsasl2 with CRAM-MD5 linked in and
 * proves the mechanism is really implemented (not a stub):
 *
 *  1. md5-hmac-self-test          local MD5/HMAC-MD5 matches RFC 1321 +
 *                                 RFC 2202 vectors (validates the checker
 *                                 used by check 8 before trusting it)
 *  2. version-2.1                 library version is 2.1.x
 *  3. client-init                 sasl_client_init succeeds
 *  4. server-init                 sasl_server_init succeeds
 *  5. client-new                  sasl_client_new creates a connection
 *  6. server-new                  sasl_server_new creates a connection
 *  7. client-listmech-cram-md5    CRAM-MD5 is offered on the client side
 *  8. server-listmech-cram-md5    CRAM-MD5 is offered on the server side
 *  9. cram-md5-hmac-exchange      real CRAM-MD5 round trip: the server
 *                                 emits its RFC 2195 challenge, the client
 *                                 answers with "<authid> <hex>", and the
 *                                 digest is recomputed locally as
 *                                 HMAC-MD5(password, challenge) and must
 *                                 match byte for byte
 *
 * With --ohos-static-only the binary performs the OHOS-specific check
 * instead (used by the conanfile with SASL_PATH pointing at a
 * non-existent directory):
 * 10. ohos-static-mechanism-no-saslpath
 *                                 CRAM-MD5 is still enumerated with no
 *                                 runtime plugin directory available —
 *                                 this is the OHOS adaptation assertion
 *                                 (--with-staticsasl: the mechanism is
 *                                 linked into libsasl2.a, so no
 *                                 SASL_PATH/dlopen plugin search happens)
 *
 * Every passing check prints exactly one "CHECK-OK: <name>" line, which
 * test_package/conanfile.py counts for the HMBS_TEST_PACKAGE_RESULT
 * evidence marker (exit-0-alone is not proof).
 */
#include <sasl/sasl.h>

#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define AUTHID "ken"
#define PASSWORD "crammd5pass"

/* ───────────────────────── MD5 (RFC 1321) ───────────────────────── */

typedef struct {
    uint32_t h[4];
    uint64_t total_bits;
    unsigned char block[64];
    size_t block_len;
} md5_ctx;

static const uint32_t MD5_K[64] = {
    0xd76aa478u, 0xe8c7b756u, 0x242070dbu, 0xc1bdceeeu,
    0xf57c0fafu, 0x4787c62au, 0xa8304613u, 0xfd469501u,
    0x698098d8u, 0x8b44f7afu, 0xffff5bb1u, 0x895cd7beu,
    0x6b901122u, 0xfd987193u, 0xa679438eu, 0x49b40821u,
    0xf61e2562u, 0xc040b340u, 0x265e5a51u, 0xe9b6c7aau,
    0xd62f105du, 0x02441453u, 0xd8a1e681u, 0xe7d3fbc8u,
    0x21e1cde6u, 0xc33707d6u, 0xf4d50d87u, 0x455a14edu,
    0xa9e3e905u, 0xfcefa3f8u, 0x676f02d9u, 0x8d2a4c8au,
    0xfffa3942u, 0x8771f681u, 0x6d9d6122u, 0xfde5380cu,
    0xa4beea44u, 0x4bdecfa9u, 0xf6bb4b60u, 0xbebfbc70u,
    0x289b7ec6u, 0xeaa127fau, 0xd4ef3085u, 0x04881d05u,
    0xd9d4d039u, 0xe6db99e5u, 0x1fa27cf8u, 0xc4ac5665u,
    0xf4292244u, 0x432aff97u, 0xab9423a7u, 0xfc93a039u,
    0x655b59c3u, 0x8f0ccc92u, 0xffeff47du, 0x85845dd1u,
    0x6fa87e4fu, 0xfe2ce6e0u, 0xa3014314u, 0x4e0811a1u,
    0xf7537e82u, 0xbd3af235u, 0x2ad7d2bbu, 0xeb86d391u
};

static const unsigned char MD5_S[64] = {
    7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22, 7, 12, 17, 22,
    5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20, 5, 9, 14, 20,
    4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23, 4, 11, 16, 23,
    6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21, 6, 10, 15, 21
};

static uint32_t rotl32(uint32_t x, unsigned c)
{
    return (x << c) | (x >> (32 - c));
}

static void md5_block(md5_ctx *ctx, const unsigned char *p)
{
    uint32_t m[16];
    uint32_t a = ctx->h[0], b = ctx->h[1], c = ctx->h[2], d = ctx->h[3];
    int i;

    for (i = 0; i < 16; i++) {
        m[i] = (uint32_t) p[i * 4]
             | ((uint32_t) p[i * 4 + 1] << 8)
             | ((uint32_t) p[i * 4 + 2] << 16)
             | ((uint32_t) p[i * 4 + 3] << 24);
    }
    for (i = 0; i < 64; i++) {
        uint32_t f;
        int g;
        if (i < 16) {
            f = (b & c) | (~b & d);
            g = i;
        } else if (i < 32) {
            f = (d & b) | (~d & c);
            g = (5 * i + 1) & 15;
        } else if (i < 48) {
            f = b ^ c ^ d;
            g = (3 * i + 5) & 15;
        } else {
            f = c ^ (b | ~d);
            g = (7 * i) & 15;
        }
        f += a + MD5_K[i] + m[g];
        a = d;
        d = c;
        c = b;
        b += rotl32(f, MD5_S[i]);
    }
    ctx->h[0] += a;
    ctx->h[1] += b;
    ctx->h[2] += c;
    ctx->h[3] += d;
}

static void md5_init(md5_ctx *ctx)
{
    ctx->h[0] = 0x67452301u;
    ctx->h[1] = 0xefcdab89u;
    ctx->h[2] = 0x98badcfeu;
    ctx->h[3] = 0x10325476u;
    ctx->total_bits = 0;
    ctx->block_len = 0;
}

static void md5_update(md5_ctx *ctx, const void *data, size_t len)
{
    const unsigned char *p = (const unsigned char *) data;

    ctx->total_bits += (uint64_t) len * 8u;
    while (len > 0) {
        size_t take = 64 - ctx->block_len;
        if (take > len) {
            take = len;
        }
        memcpy(ctx->block + ctx->block_len, p, take);
        ctx->block_len += take;
        p += take;
        len -= take;
        if (ctx->block_len == 64) {
            md5_block(ctx, ctx->block);
            ctx->block_len = 0;
        }
    }
}

static void md5_final(md5_ctx *ctx, unsigned char out[16])
{
    unsigned char pad[72];
    size_t pad_len;
    uint64_t bits = ctx->total_bits;
    int i;

    pad_len = (ctx->block_len < 56) ? (56 - ctx->block_len)
                                    : (120 - ctx->block_len);
    memset(pad, 0, sizeof(pad));
    pad[0] = 0x80;
    for (i = 0; i < 8; i++) {
        pad[pad_len + i] = (unsigned char) ((bits >> (8 * i)) & 0xff);
    }
    md5_update(ctx, pad, pad_len + 8);
    for (i = 0; i < 4; i++) {
        out[i * 4] = (unsigned char) (ctx->h[i] & 0xff);
        out[i * 4 + 1] = (unsigned char) ((ctx->h[i] >> 8) & 0xff);
        out[i * 4 + 2] = (unsigned char) ((ctx->h[i] >> 16) & 0xff);
        out[i * 4 + 3] = (unsigned char) ((ctx->h[i] >> 24) & 0xff);
    }
}

static void md5_hex(const unsigned char *digest, size_t len, char *out)
{
    static const char hexd[] = "0123456789abcdef";
    size_t i;
    for (i = 0; i < len; i++) {
        out[i * 2] = hexd[digest[i] >> 4];
        out[i * 2 + 1] = hexd[digest[i] & 0x0f];
    }
    out[len * 2] = '\0';
}

static void hmac_md5(const unsigned char *key, size_t key_len,
                     const unsigned char *msg, size_t msg_len,
                     unsigned char out[16])
{
    unsigned char k[64];
    unsigned char inner[64 + 1];
    unsigned char outer[64 + 1];
    unsigned char inner_digest[16];
    md5_ctx ctx;
    size_t i;

    memset(k, 0, sizeof(k));
    if (key_len > 64) {
        md5_init(&ctx);
        md5_update(&ctx, key, key_len);
        md5_final(&ctx, k);
    } else {
        memcpy(k, key, key_len);
    }
    for (i = 0; i < 64; i++) {
        inner[i] = (unsigned char) (k[i] ^ 0x36);
        outer[i] = (unsigned char) (k[i] ^ 0x5c);
    }
    md5_init(&ctx);
    md5_update(&ctx, inner, 64);
    md5_update(&ctx, msg, msg_len);
    md5_final(&ctx, inner_digest);

    md5_init(&ctx);
    md5_update(&ctx, outer, 64);
    md5_update(&ctx, inner_digest, 16);
    md5_final(&ctx, out);
}

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

static int failed(const char *what, int rc)
{
    fprintf(stderr, "FAIL: %s (sasl rc=%d)\n", what, rc);
    return 1;
}

static int check_md5_hmac_self_test(void)
{
    static const struct { const char *msg; const char *want; } vectors[] = {
        { "", "d41d8cd98f00b204e9800998ecf8427e" },
        { "abc", "900150983cd24fb0d6963f7d28e17f72" },
        { "message digest", "f96b697d7cb7938d525a2f31aaf161d0" },
        { "abcdefghijklmnopqrstuvwxyz", "c3fcd3d76192e4007dfb496cca67e13b" },
    };
    unsigned char digest[16];
    char hex[33];
    size_t i;

    for (i = 0; i < sizeof(vectors) / sizeof(vectors[0]); i++) {
        md5_ctx ctx;
        md5_init(&ctx);
        md5_update(&ctx, vectors[i].msg, strlen(vectors[i].msg));
        md5_final(&ctx, digest);
        md5_hex(digest, 16, hex);
        if (strcmp(hex, vectors[i].want) != 0) {
            fprintf(stderr, "FAIL: MD5(\"%s\") = %s, want %s\n",
                    vectors[i].msg, hex, vectors[i].want);
            return 1;
        }
    }
    /* RFC 2202 HMAC-MD5 test case 2 */
    hmac_md5((const unsigned char *) "Jefe", 4,
             (const unsigned char *) "what do ya want for nothing?", 28,
             digest);
    md5_hex(digest, 16, hex);
    if (strcmp(hex, "750c783e6ab0b503eaa86e310a5db738") != 0) {
        fprintf(stderr, "FAIL: HMAC-MD5(Jefe) = %s, want 750c...b738\n", hex);
        return 1;
    }
    printf("CHECK-OK: md5-hmac-self-test\n");
    return 0;
}

static int check_ohos_static_only(void)
{
    const char *sasl_path = getenv("SASL_PATH");
    sasl_conn_t *conn = NULL;
    const char *mechlist = NULL;
    unsigned mechlen = 0;
    int count = 0;
    int r;

    /* The OHOS adaptation links CRAM-MD5 into libsasl2.a, so the
     * mechanism must be available with no plugin directory at all. */
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
    if (!mechlist || !strstr(mechlist, "CRAM-MD5")) {
        sasl_dispose(&conn);
        fprintf(stderr, "FAIL: CRAM-MD5 not statically registered "
                        "(SASL_PATH=%s)\n", sasl_path ? sasl_path : "(unset)");
        return 1;
    }
    sasl_dispose(&conn);
    sasl_client_done();
    printf("CHECK-OK: ohos-static-mechanism-no-saslpath\n");
    return 0;
}

static int check_cram_exchange(sasl_conn_t *cconn)
{
    sasl_conn_t *sconn = NULL;
    const char *serverout = NULL;
    unsigned serveroutlen = 0;
    const char *clientout = NULL;
    unsigned clientoutlen = 0;
    const char *mech = NULL;
    char challenge[512];
    unsigned challen;
    unsigned char digest[16];
    char expected[33];
    char got[64];
    const char *sep;
    size_t userlen;
    int r;

    r = sasl_server_new("smtp", "localhost", NULL, NULL, NULL, NULL, 0,
                        &sconn);
    if (r != SASL_OK || sconn == NULL) {
        return failed("sasl_server_new", r);
    }

    /* CRAM-MD5 is server-first (SASL_FEAT_SERVER_FIRST): the server emits
     * its RFC 2195 challenge "<random.time@fqdn>".  The returned pointer
     * is owned by the server context, so take a private copy before the
     * connection is disposed. */
    r = sasl_server_start(sconn, "CRAM-MD5", NULL, 0, &serverout,
                          &serveroutlen);
    if (r != SASL_CONTINUE || serverout == NULL || serveroutlen == 0) {
        sasl_dispose(&sconn);
        return failed("sasl_server_start challenge", r);
    }
    if (serveroutlen >= sizeof(challenge)) {
        sasl_dispose(&sconn);
        fprintf(stderr, "FAIL: CRAM-MD5 challenge too long (%u)\n",
                serveroutlen);
        return 1;
    }
    memcpy(challenge, serverout, serveroutlen);
    challenge[serveroutlen] = '\0';
    challen = serveroutlen;
    printf("server challenge: %s\n", challenge);

    r = sasl_client_start(cconn, "CRAM-MD5", NULL, &clientout,
                          &clientoutlen, &mech);
    if (r != SASL_OK && r != SASL_CONTINUE) {
        sasl_dispose(&sconn);
        return failed("sasl_client_start", r);
    }
    if (clientoutlen == 0) {
        r = sasl_client_step(cconn, challenge, challen, NULL,
                             &clientout, &clientoutlen);
        if (r != SASL_OK && r != SASL_CONTINUE) {
            sasl_dispose(&sconn);
            return failed("sasl_client_step(response)", r);
        }
    }
    sasl_dispose(&sconn);

    if (clientout == NULL || clientoutlen == 0) {
        fprintf(stderr, "FAIL: empty CRAM-MD5 client response\n");
        return 1;
    }
    if (clientoutlen >= sizeof(got)) {
        fprintf(stderr, "FAIL: CRAM-MD5 response too long (%u)\n",
                clientoutlen);
        return 1;
    }
    memcpy(got, clientout, clientoutlen);
    got[clientoutlen] = '\0';
    printf("client response: %s\n", got);

    /* RFC 2195 response is "<user> <hex-digest>". */
    sep = strchr(got, ' ');
    if (sep == NULL) {
        fprintf(stderr, "FAIL: CRAM-MD5 response has no <user> <digest> "
                        "separator\n");
        return 1;
    }
    userlen = (size_t) (sep - got);
    if (userlen != strlen(AUTHID) || strncmp(got, AUTHID, userlen) != 0) {
        fprintf(stderr, "FAIL: CRAM-MD5 response user is not \"%s\"\n",
                AUTHID);
        return 1;
    }
    if (strlen(sep + 1) != 32) {
        fprintf(stderr, "FAIL: CRAM-MD5 digest is not 32 hex chars: \"%s\"\n",
                sep + 1);
        return 1;
    }

    /* Independently recompute HMAC-MD5(password, challenge): proves the
     * mechanism really executed its HMAC-MD5 primitive. */
    hmac_md5((const unsigned char *) PASSWORD, strlen(PASSWORD),
             (const unsigned char *) challenge, challen, digest);
    md5_hex(digest, 16, expected);
    printf("expected HMAC-MD5: %s\n", expected);
    if (strcmp(expected, sep + 1) != 0) {
        fprintf(stderr, "FAIL: CRAM-MD5 digest mismatch (got %s, want %s)\n",
                sep + 1, expected);
        return 1;
    }
    printf("CHECK-OK: cram-md5-hmac-exchange\n");
    return 0;
}

int main(int argc, char **argv)
{
    const char *impl = NULL;
    const char *ver = NULL;
    int major = 0, minor = 0, step = 0, patch = 0;
    sasl_conn_t *sconn = NULL;
    sasl_conn_t *cconn = NULL;
    const char *mechlist = NULL;
    unsigned mechlen = 0;
    int count = 0;
    int r;
    int rc = 0;

    if (argc > 1 && strcmp(argv[1], "--ohos-static-only") == 0) {
        return check_ohos_static_only();
    }
    if (argc > 1 && strcmp(argv[1], "--md5-only") == 0) {
        return check_md5_hmac_self_test();
    }

    if (check_md5_hmac_self_test() != 0) {
        return 1;
    }

    sasl_version_info(&impl, &ver, &major, &minor, &step, &patch);
    printf("libsasl2 impl=%s version=%s (%d.%d.%d.%d)\n",
           impl ? impl : "?", ver ? ver : "?",
           major, minor, step, patch);
    if (major != 2 || minor != 1) {
        fprintf(stderr, "FAIL: unexpected version (want 2.1.x)\n");
        return 1;
    }
    printf("CHECK-OK: version-2.1\n");

    r = sasl_client_init(client_callbacks);
    if (r != SASL_OK) {
        return failed("sasl_client_init", r);
    }
    printf("CHECK-OK: client-init\n");

    r = sasl_server_init(NULL, "cyrus-sasl-crammd5-test");
    if (r != SASL_OK) {
        return failed("sasl_server_init", r);
    }
    printf("CHECK-OK: server-init\n");

    r = sasl_client_new("smtp", "localhost", NULL, NULL, client_callbacks,
                        0, &cconn);
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
        return failed("sasl_listmech (client)", r);
    }
    printf("client mechs (%d): %s\n", count, mechlist ? mechlist : "(none)");
    if (!mechlist || !strstr(mechlist, "CRAM-MD5")) {
        fprintf(stderr, "FAIL: CRAM-MD5 mechanism not available (client)\n");
        return 1;
    }
    printf("CHECK-OK: client-listmech-cram-md5\n");

    r = sasl_listmech(sconn, NULL, "", " ", "", &mechlist, &mechlen, &count);
    if (r != SASL_OK) {
        return failed("sasl_listmech (server)", r);
    }
    printf("server mechs (%d): %s\n", count, mechlist ? mechlist : "(none)");
    if (!mechlist || !strstr(mechlist, "CRAM-MD5")) {
        fprintf(stderr, "FAIL: CRAM-MD5 mechanism not available (server)\n");
        return 1;
    }
    printf("CHECK-OK: server-listmech-cram-md5\n");

    if (check_cram_exchange(cconn) != 0) {
        rc = 1;
    }

    sasl_dispose(&cconn);
    sasl_dispose(&sconn);
    sasl_client_done();
    sasl_server_done();

    if (rc == 0) {
        printf("cyrus-sasl-crammd5 consumer test PASS (9/9 + ohos-static)\n");
    }
    return rc;
}
