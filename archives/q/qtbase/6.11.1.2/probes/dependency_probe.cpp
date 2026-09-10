#include <dbus/dbus.h>
#include <cstdio>
#include <expat.h>
#include <openssl/ssl.h>
#include <wayland-client.h>
#include <wayland-cursor.h>
#include <wayland-egl.h>
#include <wayland-server.h>
#include <xkbcommon/xkbcommon.h>

// Exported references retain cursor/EGL relocations even in optimized builds.
auto qtbase_cursor_api = &wl_cursor_image_get_buffer;
auto qtbase_egl_api = &wl_egl_window_get_attached_size;

static int failed(int stage, const char *operation)
{
    std::fprintf(stderr, "[FAIL] dependency stage %d: %s\n", stage, operation);
    return stage;
}

extern "C" int qtbase_dependency_probe()
{
    DBusMessage *message = dbus_message_new_signal("/org/qtproject/Probe", "org.qtproject.Probe", "Ready");
    if (!message)
        return failed(1, "dbus_message_new_signal");
    dbus_message_unref(message);
    SSL_CTX *ssl = SSL_CTX_new(TLS_method());
    if (!ssl)
        return failed(2, "SSL_CTX_new");
    SSL_CTX_free(ssl);
    xkb_context *keyboard = xkb_context_new(XKB_CONTEXT_NO_DEFAULT_INCLUDES);
    if (!keyboard)
        return failed(3, "xkb_context_new");
    xkb_context_unref(keyboard);
    if (wl_display_interface.version < 1)
        return failed(4, "wl_display_interface.version");
    XML_Parser parser = XML_ParserCreate(nullptr);
    if (!parser)
        return failed(5, "XML_ParserCreate");
    XML_ParserFree(parser);
    wl_event_loop *loop = wl_event_loop_create();
    if (!loop)
        return failed(6, "wl_event_loop_create");
    wl_event_loop_destroy(loop);
    return 0;
}
