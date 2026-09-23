/* test_tls_backend.c — validate that glib-networking activated a real TLS
 * backend (not GDummyTlsBackend) and that a process-level TLS handshake path
 * runs through the real backend. Uses only synchronous GLib 2.88 API. */
#include <glib.h>
#include <gio/gio.h>
#include <stdio.h>
#include <string.h>

static int g_passed = 0;
static int g_failed = 0;

#define CHECK(cond, msg)                                     \
    do {                                                    \
        if (cond) {                                         \
            g_printerr("PASS: %s\n", msg);                  \
            g_passed++;                                     \
        } else {                                            \
            g_printerr("FAIL: %s\n", msg);                  \
            g_failed++;                                     \
        }                                                   \
    } while (0)

int main(int argc, char **argv) {
    GTlsBackend *backend = g_tls_backend_get_default();
    CHECK(backend != NULL, "g_tls_backend_get_default() returns non-NULL");

    const char *type_name = G_OBJECT_TYPE_NAME(G_OBJECT(backend));
    g_printerr("backend type: %s\n", type_name);
    /* GDummyTlsBackend ships inside libgio; a real backend (GTlsBackendOpenssl)
     * only exists when glib-networking's gioopenssl module is loaded. */
    if (type_name != NULL && strstr(type_name, "Dummy") != NULL) {
        g_printerr("ERROR: still GDummyTlsBackend — glib-networking module not loaded\n");
        g_failed++;
        return 1;
    }
    CHECK(g_tls_backend_supports_tls(backend), "backend supports TLS");
    GType cert_type = g_tls_backend_get_certificate_type(backend);
    CHECK(cert_type != G_TYPE_INVALID, "backend exposes a certificate type");

    /* Process-level exercise: build a local TCP socket pair and drive a
     * GTlsClientConnection handshake through the real backend. A handshake
     * against a plain (non-TLS) peer must fail with a TLS error from the
     * openssl backend — proving the module's code path executed (GDummy
     * short-circuits and never reaches a handshake). */
    GError *err = NULL;
    GSocket *server = g_socket_new(G_SOCKET_FAMILY_IPV4, G_SOCKET_TYPE_STREAM,
                                   G_SOCKET_PROTOCOL_TCP, &err);
    CHECK(server != NULL, "created server GSocket");
    if (!server) {
        g_printerr("socket create failed: %s\n", err ? err->message : "unknown");
        return 1;
    }
    GInetAddress *loop = g_inet_address_new_loopback(G_SOCKET_FAMILY_IPV4);
    GSocketAddress *addr = g_inet_socket_address_new(loop, 0);
    gboolean ok = g_socket_bind(server, addr, TRUE, &err);
    CHECK(ok, "server socket bound");
    if (!ok) {
        g_printerr("bind failed: %s\n", err ? err->message : "unknown");
        return 1;
    }
    ok = g_socket_listen(server, &err);
    CHECK(ok, "server socket listening");
    if (!ok) {
        g_printerr("listen failed: %s\n", err ? err->message : "unknown");
        return 1;
    }
    GSocketAddress *bound = g_socket_get_local_address(server, &err);
    guint16 port = g_inet_socket_address_get_port(G_INET_SOCKET_ADDRESS(bound));

    GSocket *client = g_socket_new(G_SOCKET_FAMILY_IPV4, G_SOCKET_TYPE_STREAM,
                                   G_SOCKET_PROTOCOL_TCP, &err);
    GSocketAddress *caddr = g_inet_socket_address_new(loop, port);
    ok = g_socket_connect(client, caddr, NULL, &err);
    CHECK(ok, "client socket connected");
    if (!ok) {
        g_printerr("connect failed: %s\n", err ? err->message : "unknown");
        return 1;
    }

    /* Accept the pending client on the server side, send plain-text garbage
     * and close: the TLS client then fails its handshake immediately with a
     * real backend error instead of waiting on a silent peer. */
    GSocket *accepted = g_socket_accept(server, NULL, &err);
    CHECK(accepted != NULL, "server accepted the client connection");
    if (accepted) {
        const gchar *garbage = "NOT-A-TLS-SERVER\r\n\r\n";
        g_socket_send(accepted, garbage, (gssize)strlen(garbage), NULL, NULL);
        g_socket_close(accepted, NULL);
        g_object_unref(accepted);
    }

    GSocketConnection *conn = g_socket_connection_factory_create_connection(client);
    GTlsClientConnection *tls_conn = g_tls_client_connection_new(G_IO_STREAM(conn), NULL, &err);
    CHECK(tls_conn != NULL, "created GTlsClientConnection through real backend");
    if (!tls_conn) {
        g_printerr("tls client create failed: %s\n", err ? err->message : "unknown");
        return 1;
    }
    g_printerr("GTlsClientConnection type: %s\n",
               G_OBJECT_TYPE_NAME(G_OBJECT(tls_conn)));

    /* Handshake against a non-TLS peer: must fail with a real TLS error from
     * the openssl backend, not hang and not abort. */
    gboolean hs = g_tls_connection_handshake(G_TLS_CONNECTION(tls_conn), NULL, &err);
    CHECK(!hs && err != NULL, "handshake returned a backend TLS error (real module code path)");
    if (err) {
        g_printerr("TLS handshake error (expected for non-TLS peer): %s\n", err->message);
        g_error_free(err);
    }
    g_io_stream_close(G_IO_STREAM(conn), NULL, NULL);

    g_printerr("RESULT: %d passed, %d failed\n", g_passed, g_failed);
    return g_failed == 0 ? 0 : 1;
}