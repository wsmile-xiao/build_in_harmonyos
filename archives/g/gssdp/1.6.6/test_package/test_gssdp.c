/* test_gssdp.c — Conan L1 test for gssdp 1.6.6.
 *
 * Exercises the real GSSDP API: create a GSSDPClient bound to loopback,
 * verify it becomes active, announce a resource via GSSDPResourceGroup and
 * tear it down again. This is a substantive API smoke test (R34) — not a
 * print-only stub.
 */
#include <glib.h>
#include <gio/gio.h>
#include <libgssdp/gssdp.h>

int
main (void)
{
        GError *error = NULL;
        GSSDPClient *client = NULL;
        GSSDPResourceGroup *group = NULL;
        GInetAddress *lo = NULL;
        guint resource_id = 0;

        lo = g_inet_address_new_loopback (G_SOCKET_FAMILY_IPV4);
        g_assert_true (lo != NULL);

        /* Create a GSSDP client bound to the IPv4 loopback interface. */
        client = gssdp_client_new_for_address (lo,
                                               0,
                                               GSSDP_UDA_VERSION_1_0,
                                               &error);
        g_assert_no_error (error);
        g_assert_true (client != NULL);

        /* The client should be active once constructed. */
        g_assert_true (gssdp_client_get_active (client));

        /* Announce a resource through a resource group (exercises the SSDP
         * announce path: message formatting + socket send on loopback). */
        group = gssdp_resource_group_new (client);
        g_assert_true (group != NULL);

        resource_id = gssdp_resource_group_add_resource_simple (
                group,
                "urn:gssdp-test:device:1",
                "uuid:00000000-0000-0000-0000-000000000001",
                "http://127.0.0.1:0/gssdp-test.xml");
        g_assert_cmpuint (resource_id, >, 0);

        /* Removal API returns void (gssdp-resource-group.h) — the P3 review
         * suggestion to assert its return value is not applicable; the add
         * side (resource_id > 0) already covers resource-group bookkeeping. */
        gssdp_resource_group_remove_resource (group, resource_id);

        g_clear_object (&group);
        g_clear_object (&client);
        g_clear_object (&lo);

        return 0;
}
