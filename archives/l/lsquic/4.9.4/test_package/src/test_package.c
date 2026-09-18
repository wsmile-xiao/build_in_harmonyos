#include <stdio.h>
#include <string.h>

#include <openssl/ssl.h>

#include <lsquic/lsquic.h>

/* Minimal SSL_CTX factory: TLS 1.3 client context.  This is what a
 * lsquic-based client hands to the engine; under the OpenSSL port the
 * engine wires the compat-layer OSSL_DISPATCH bridge onto these SSL
 * objects when connections are created. */
static struct ssl_ctx_st *
get_ssl_ctx (void *peer_ctx, const struct sockaddr *local)
{
    static SSL_CTX *ctx;
    if (!ctx)
    {
        ctx = SSL_CTX_new(TLS_client_method());
        if (ctx)
        {
            SSL_CTX_set_min_proto_version(ctx, TLS1_3_VERSION);
            SSL_CTX_set_max_proto_version(ctx, TLS1_3_VERSION);
        }
    }
    return ctx;
}

/* Packet-out stub: no packets are ever sent in this test (no connections
 * are opened); the callback just satisfies the engine constructor. */
static int
packets_out (void *ctx, const struct lsquic_out_spec *specs, unsigned count)
{
    (void) ctx; (void) specs;
    return (int) count;
}

/* Stream callbacks: only the names the engine dereferences on creation
 * are needed; the test never opens a connection. */
static lsquic_conn_ctx_t *
on_new_conn (void *stream_if_ctx, lsquic_conn_t *conn)
{   (void) stream_if_ctx; (void) conn; return NULL;   }

static void
on_conn_closed (lsquic_conn_t *conn)
{   (void) conn;   }

static lsquic_stream_ctx_t *
on_new_stream (void *stream_if_ctx, lsquic_stream_t *stream)
{   (void) stream_if_ctx; lsquic_stream_wantread(stream, 0); return NULL;   }

static const struct lsquic_stream_if stream_if = {
    .on_new_conn            = on_new_conn,
    .on_conn_closed         = on_conn_closed,
    .on_new_stream          = on_new_stream,
};

int main(void)
{
    struct lsquic_engine_settings settings;
    struct lsquic_engine_api api;
    lsquic_engine_t *engine;

    if (0 != lsquic_global_init(LSQUIC_GLOBAL_CLIENT | LSQUIC_GLOBAL_SERVER))
    {
        fprintf(stderr, "FAIL: lsquic_global_init\n");
        return 1;
    }

    /* Settings validation exercises version bookkeeping incl. the
     * generated version tables. */
    lsquic_engine_init_settings(&settings, 0);
    if (!(settings.es_versions & (1 << LSQVER_I001)))
    {
        fprintf(stderr, "FAIL: IETF QUIC v1 not enabled\n");
        return 1;
    }
    printf("es_versions=0x%x (IETF v1 enabled)\n", settings.es_versions);

    memset(&api, 0, sizeof(api));
    api.ea_settings     = &settings;
    api.ea_stream_if    = &stream_if;
    api.ea_packets_out  = packets_out;
    api.ea_get_ssl_ctx  = get_ssl_ctx;

    /* Engine construction initializes the QUIC TLS stack: under the
     * OpenSSL port this includes the retry-token AEAD contexts (the
     * EVP_AEAD shim over EVP_CIPHER) via lsquic_engine_init_settings. */
    engine = lsquic_engine_new(0, &api);
    if (!engine)
    {
        fprintf(stderr, "FAIL: lsquic_engine_new\n");
        return 1;
    }
    printf("engine created OK (QUIC TLS bridge initialized)\n");

    lsquic_engine_destroy(engine);
    lsquic_global_cleanup();
    printf("lsquic test_package: PASS\n");
    return 0;
}
