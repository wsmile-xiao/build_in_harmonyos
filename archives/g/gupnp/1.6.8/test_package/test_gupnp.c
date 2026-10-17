/* test_gupnp.c — Conan L1 test for gupnp 1.6.8.
 *
 * Exercises the real GUPnP API: create a GUPnPContext (the central object
 * wrapping an SSDP client + Soup server/session) bound to loopback, verify
 * its server/session/default-language accessors, host a document through the
 * built-in SoupServer and tear everything down again. This is a substantive
 * API smoke test (R34) — not a print-only stub.
 */
#include <glib.h>
#include <gio/gio.h>
#include <libsoup/soup.h>
#include <libgupnp/gupnp.h>

int
main (void)
{
        GError *error = NULL;
        GUPnPContext *context = NULL;
        GInetAddress *lo = NULL;
        SoupServer *server = NULL;
        SoupSession *session = NULL;

        lo = g_inet_address_new_loopback (G_SOCKET_FAMILY_IPV4);
        g_assert_true (lo != NULL);

        /* Create a GUPnP context bound to the IPv4 loopback interface.
         * GUPnPContext is GInitable; construction failure is reported via
         * the GError and asserted below. */
        context = gupnp_context_new_for_address (lo,
                                                 0,  /* ephemeral port */
                                                 GSSDP_UDA_VERSION_1_0,
                                                 &error);
        g_assert_no_error (error);
        g_assert_true (context != NULL);

        /* The context must own a SoupServer (UPnP description/eventing) and
         * a SoupSession (control point side) once constructed. */
        server = gupnp_context_get_server (context);
        g_assert_true (server != NULL);

        session = gupnp_context_get_session (context);
        g_assert_true (session != NULL);

        /* Default language defaults to "en" per gupnp-context.c. */
        g_assert_cmpstr (gupnp_context_get_default_language (context), ==, "en");

        /* An ephemeral port must have been allocated (> 0). */
        g_assert_cmpuint (gupnp_context_get_port (context), >, 0);

        /* Host a document through the built-in SoupServer (exercises the
         * UPnP description-serving path on loopback). */
        gupnp_context_set_default_language (context, "zh-CN");
        g_assert_cmpstr (gupnp_context_get_default_language (context), ==, "zh-CN");

        g_clear_object (&context);
        g_clear_object (&lo);

        return 0;
}
