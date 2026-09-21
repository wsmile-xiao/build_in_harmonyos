/* Validates libnm 1.52.1 through its real public API (R34: no empty-shell
 * test). Everything asserted below works in an isolated sandbox - there is no
 * NetworkManager daemon and no system D-Bus - so the NMClient object itself is
 * only type-checked, while NMConnection / NMSetting / NMIPAddress and the
 * nm_utils_* helpers are exercised end to end, including a full GVariant
 * (D-Bus) serialisation round trip.
 *
 * The connection round trip runs the same setting validators and the same
 * GVariant marshalling nmcli and the daemon use, which is exactly the code the
 * OHOS adaption of this library touches.
 *
 * The two system headers are included first on purpose: that is the order a
 * normal consumer uses, and it is the order under which the OHOS sysroot's
 * sockaddr_storage handling (knowledge base E091/E119) would show up.
 *
 * The public header is spelled <NetworkManager.h>, not <libnm/NetworkManager.h>:
 * upstream installs the headers into <prefix>/include/libnm and points the
 * include path at that directory itself ("Cflags: -I${includedir}/libnm" in
 * libnm.pc). The package declares the same directory through
 * cpp_info.includedirs = ["include/libnm"], so #include <NetworkManager.h> is
 * the spelling that works for both pkg-config and CMake consumers. Every
 * header below that one is reached with quote-relative includes, exactly as
 * upstream ships them. */
#include <netinet/in.h>
#include <sys/socket.h>

#include <NetworkManager.h>

#include <glib.h>
#include <stdio.h>
#include <string.h>

static int failures;

#define CHECK(cond, msg)                                                     \
    do {                                                                     \
        if (!(cond)) {                                                       \
            g_printerr("FAIL %s:%d: %s\n", __FILE__, __LINE__, (msg));       \
            failures++;                                                      \
        }                                                                    \
    } while (0)

int
main(void)
{
    gchar        *uuid    = NULL;
    NMConnection *conn    = NULL;
    NMConnection *parsed  = NULL;
    NMSetting    *s_con   = NULL;
    NMSetting    *s_wired = NULL;
    NMSetting    *s_ip4   = NULL;
    NMIPAddress  *addr    = NULL;
    GVariant     *variant = NULL;
    GError       *error   = NULL;

    /* 1. The installed library and the installed headers must agree on the
     *    version. nm_utils_version() returns
     *    (major << 16 | minor << 8 | micro). */
    CHECK(NM_MAJOR_VERSION == 1 && NM_MINOR_VERSION == 52 && NM_MICRO_VERSION == 1,
          "installed headers do not report version 1.52.1");
    CHECK(nm_utils_version()
              == (guint) ((NM_MAJOR_VERSION << 16) | (NM_MINOR_VERSION << 8)
                          | NM_MICRO_VERSION),
          "nm_utils_version() does not match the installed version headers");

    /* 2. nm_utils_* helpers implemented on top of GLib. */
    uuid = nm_utils_uuid_generate();
    CHECK(uuid != NULL, "nm_utils_uuid_generate() returned NULL");
    /* nm_utils_is_uuid() is the only *public* UUID predicate upstream ships:
     * it was deprecated in 1.32 in favour of the internal nm_uuid_is_valid_*()
     * helpers, which are neither installed nor exported (verified against the
     * shipped headers and `nm -D libnm.so`). The deprecation is therefore
     * silenced rather than worked around - the API is still the right one to
     * assert that the library accepts the UUID it just produced. */
G_GNUC_BEGIN_IGNORE_DEPRECATIONS
    CHECK(uuid != NULL && nm_utils_is_uuid(uuid),
          "nm_utils_uuid_generate() did not produce a valid UUID");
    CHECK(nm_utils_is_uuid("not-a-uuid") == FALSE,
          "nm_utils_is_uuid() accepted a non-UUID string");
G_GNUC_END_IGNORE_DEPRECATIONS
    if (!uuid)
        goto out;

    /* 3. Build a real profile out of settings. This drives NMConnection,
     *    NMSettingConnection, NMSettingWired, NMSettingIP4Config and
     *    NMIPAddress. */
    conn = nm_simple_connection_new();
    CHECK(conn != NULL, "nm_simple_connection_new() returned NULL");
    if (!conn)
        goto out;

    s_con = nm_setting_connection_new();
    g_object_set(s_con,
                 NM_SETTING_CONNECTION_ID, "libnm-test",
                 NM_SETTING_CONNECTION_UUID, uuid,
                 NM_SETTING_CONNECTION_TYPE, "802-3-ethernet",
                 NM_SETTING_CONNECTION_INTERFACE_NAME, "nmlibtest0",
                 NULL);
    nm_connection_add_setting(conn, s_con);

    s_wired = nm_setting_wired_new();
    nm_connection_add_setting(conn, s_wired);

    s_ip4 = nm_setting_ip4_config_new();
    g_object_set(s_ip4,
                 NM_SETTING_IP_CONFIG_METHOD, NM_SETTING_IP4_CONFIG_METHOD_MANUAL,
                 NULL);
    addr = nm_ip_address_new(AF_INET, "192.0.2.17", 24, &error);
    CHECK(addr != NULL, error ? error->message : "nm_ip_address_new() returned NULL");
    if (addr) {
        CHECK(nm_ip_address_get_prefix(addr) == 24,
              "nm_ip_address_get_prefix() returned something other than 24");
        CHECK(nm_setting_ip_config_add_address((NMSettingIPConfig *) s_ip4, addr),
              "nm_setting_ip_config_add_address() rejected a valid address");
    }
    nm_connection_add_setting(conn, s_ip4);

    /* 4. The accessors must read back what was set. */
    CHECK(nm_connection_get_id(conn) != NULL
              && strcmp(nm_connection_get_id(conn), "libnm-test") == 0,
          "nm_connection_get_id() did not return the id that was set");
    CHECK(nm_connection_get_uuid(conn) != NULL
              && strcmp(nm_connection_get_uuid(conn), uuid) == 0,
          "nm_connection_get_uuid() did not return the uuid that was set");
    CHECK(nm_connection_get_connection_type(conn) != NULL
              && strcmp(nm_connection_get_connection_type(conn), "802-3-ethernet") == 0,
          "nm_connection_get_connection_type() did not return 802-3-ethernet");
    CHECK(nm_setting_connection_get_uuid((NMSettingConnection *) s_con) != NULL
              && strcmp(nm_setting_connection_get_uuid((NMSettingConnection *) s_con),
                        uuid) == 0,
          "nm_setting_connection_get_uuid() did not return the uuid that was set");
    CHECK(nm_connection_get_setting(conn, NM_TYPE_SETTING_WIRED) != NULL,
          "nm_connection_get_setting(NM_TYPE_SETTING_WIRED) returned NULL");
    CHECK(nm_connection_get_setting(conn, NM_TYPE_SETTING_IP4_CONFIG) != NULL,
          "nm_connection_get_setting(NM_TYPE_SETTING_IP4_CONFIG) returned NULL");

    /* 5. Normalise and verify: the real setting validators, the same code
     *    path that guards every profile written by nmcli. */
    error = NULL;
    CHECK(nm_connection_normalize(conn, NULL, NULL, &error),
          error ? error->message : "nm_connection_normalize() failed");
    g_clear_error(&error);
    CHECK(nm_connection_verify(conn, &error),
          error ? error->message : "nm_connection_verify() rejected a valid profile");
    g_clear_error(&error);

    /* 6. Full GVariant (D-Bus) serialisation round trip. */
    variant = nm_connection_to_dbus(conn, NM_CONNECTION_SERIALIZE_ALL);
    CHECK(variant != NULL, "nm_connection_to_dbus() returned NULL");
    if (variant) {
        parsed = nm_simple_connection_new_from_dbus(variant, &error);
        CHECK(parsed != NULL,
              error ? error->message : "nm_simple_connection_new_from_dbus() returned NULL");
        if (parsed) {
            CHECK(nm_connection_get_uuid(parsed) != NULL
                      && strcmp(nm_connection_get_uuid(parsed), uuid) == 0,
                  "uuid did not survive the D-Bus round trip");
            CHECK(nm_connection_get_id(parsed) != NULL
                      && strcmp(nm_connection_get_id(parsed), "libnm-test") == 0,
                  "connection id did not survive the D-Bus round trip");
            CHECK(nm_connection_get_setting(parsed, NM_TYPE_SETTING_WIRED) != NULL,
                  "the wired setting did not survive the D-Bus round trip");
            CHECK(nm_connection_verify(parsed, &error),
                  error ? error->message
                        : "the deserialised profile no longer verifies");
            g_clear_error(&error);
        }
    }

    /* 7. NMClient must be a registered GObject subclass even when no daemon
     *    is reachable; only instantiating it needs the system bus, so the
     *    GType contract is what gets asserted here. */
    CHECK(nm_client_get_type() != G_TYPE_INVALID,
          "nm_client_get_type() returned G_TYPE_INVALID");
    CHECK(g_type_name(nm_client_get_type()) != NULL,
          "the NMClient GType has no registered name");
    CHECK(g_type_is_a(nm_client_get_type(), G_TYPE_OBJECT),
          "NMClient is not a GObject subclass");

out:
    g_clear_error(&error);
    g_clear_pointer(&variant, g_variant_unref);
    g_clear_object(&parsed);
    g_clear_object(&conn);
    g_clear_pointer(&addr, nm_ip_address_unref);

    if (failures > 0) {
        g_printerr("libnm 1.52.1: %d check(s) FAILED\n", failures);
        return 1;
    }

    g_print("libnm 1.52.1 OK: version=%u profile round-trip verified "
            "(normalize+verify+D-Bus), NMClient GType=%s\n",
            nm_utils_version(),
            g_type_name(nm_client_get_type()));
    return 0;
}
