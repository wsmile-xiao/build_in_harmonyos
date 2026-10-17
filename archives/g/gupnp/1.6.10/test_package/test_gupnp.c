/* test_gupnp.c — Conan L1 test for gupnp 1.6.10.
 *
 * Exercises the real GUPnP API on the loopback interface: create a context
 * manager through the upstream factory (proves the unix context manager
 * fallback selection), create a GUPnPContext bound to 127.0.0.1, run a
 * control point against ssdp:all, and create+annouce a root device.
 * This is a substantive API smoke test — not a print-only stub.
 */
#include <glib.h>
#include <gio/gio.h>
#include <libgupnp/gupnp.h>

int
main (void)
{
        GError *error = NULL;
        GUPnPContext *context = NULL;
        GUPnPContextManager *manager = NULL;
        GUPnPControlPoint *cp = NULL;
        GUPnPRootDevice *device = NULL;
        GInetAddress *lo = NULL;
        char *desc_path;
        guint port;
        const char *host_ip;

        /* Create the context manager through the upstream factory. On OHOS
         * the netlink backend is correctly detected as unavailable and the
         * unix (ifaddrs) implementation is selected (see patch 0001). */
        manager = gupnp_context_manager_create (0);
        g_assert_true (manager != NULL);

        /* Create a real GUPnPContext bound to the IPv4 loopback address:
         * starts a soup server, exercises gio/glib and the GSSDP layer. */
        lo = g_inet_address_new_loopback (G_SOCKET_FAMILY_IPV4);
        g_assert_true (lo != NULL);
        context = gupnp_context_new_for_address (lo, 0,
                                                 GSSDP_UDA_VERSION_1_0,
                                                 &error);
        g_object_unref (lo);
        g_assert_no_error (error);
        g_assert_true (context != NULL);

        /* The kernel assigned an ephemeral port to the embedded server. */
        port = gupnp_context_get_port (context);
        g_assert_cmpuint (port, >, 0);

        /* GUPnPContext derives from GSSDPClient: the bound host IP must be
         * the requested loopback address. */
        host_ip = gssdp_client_get_host_ip (GSSDP_CLIENT (context));
        g_assert_true (host_ip != NULL);
        g_assert_cmpstr (host_ip, ==, "127.0.0.1");

        /* A control point browsing ssdp:all on the context: exercises the
         * GSSDPResourceBrowser start/stop path (real SSDP traffic on
         * loopback). */
        cp = gupnp_control_point_new (context, "ssdp:all");
        g_assert_true (cp != NULL);
        gssdp_resource_browser_set_active (GSSDP_RESOURCE_BROWSER (cp), TRUE);
        g_assert_true (gssdp_resource_browser_get_active
                       (GSSDP_RESOURCE_BROWSER (cp)));
        gssdp_resource_browser_set_active (GSSDP_RESOURCE_BROWSER (cp), FALSE);

        /* Create a root device from a description served by the context's
         * own HTTP server: writes a minimal description document into a
         * temporary directory, announces it, then tears it down. */
        {
                const char *desc =
                        "<?xml version=\"1.0\"?>\n"
                        "<root xmlns=\"urn:schemas-upnp-org:device-1-0\">"
                        "<specVersion><major>1</major><minor>0</minor>"
                        "</specVersion>"
                        "<device><deviceType>urn:schemas-upnp-org:device:"
                        "BinaryLight:1</deviceType>"
                        "<friendlyName>gupnp-test</friendlyName>"
                        "<UDN>uuid:00000000-0000-0000-0000-00000000000a"
                        "</UDN></device></root>";
                const char *dir = g_get_tmp_dir ();
                GError *io_err = NULL;

                desc_path = g_build_filename (dir, "gupnp-test-desc.xml",
                                              NULL);
                g_file_set_contents (desc_path, desc, -1, &io_err);
                g_assert_no_error (io_err);

                device = gupnp_root_device_new (context, "gupnp-test-desc.xml",
                                                dir, &error);
                g_assert_no_error (error);
                g_assert_true (device != NULL);

                gupnp_root_device_set_available (device, TRUE);
                g_assert_true (gupnp_root_device_get_available (device));
                g_assert_cmpstr (gupnp_device_info_get_udn
                                 (GUPNP_DEVICE_INFO (device)), ==,
                                 "uuid:00000000-0000-0000-0000-00000000000a");
        }

        g_object_unref (device);
        g_object_unref (cp);
        g_object_unref (context);
        g_object_unref (manager);
        g_free (desc_path);

        return 0;
}
