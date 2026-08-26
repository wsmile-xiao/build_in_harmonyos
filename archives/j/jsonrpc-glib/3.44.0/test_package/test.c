#include <glib.h>
#include <jsonrpc-glib.h>

int main(void) {
    /* Create a JsonrpcServer instance — exercises gobject type system,
       glib memory allocation, and the jsonrpc-glib shared library. */
    JsonrpcServer *server = jsonrpc_server_new();
    if (server == NULL) {
        g_printerr("FAIL: jsonrpc_server_new() returned NULL\n");
        return 1;
    }
    g_object_unref(server);

    /* Verify the GType is registered */
    GType st = jsonrpc_server_get_type();
    if (st == 0) {
        g_printerr("FAIL: jsonrpc_server_get_type() returned 0\n");
        return 1;
    }

    g_print("OK: jsonrpc-glib 3.44.0 test passed\n");
    return 0;
}
