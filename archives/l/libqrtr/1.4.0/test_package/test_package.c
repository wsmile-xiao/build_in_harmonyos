#include <libqrtr-glib/libqrtr-glib.h>
#include <string.h>

static void
 test_uri_for_node_zero (void)
{
    gchar *uri = qrtr_get_uri_for_node (0);

    g_assert_cmpstr (uri, ==, "qrtr://0");
    g_free (uri);
}

static void
 test_uri_round_trip (void)
{
    guint32 node = 0;
    gchar *uri = qrtr_get_uri_for_node (42);

    g_assert_true (qrtr_get_node_for_uri (uri, &node));
    g_assert_cmpuint (node, ==, 42);
    g_free (uri);
}

static void
 test_uri_reject_invalid (void)
{
    guint32 node = 7;

    g_assert_false (qrtr_get_node_for_uri ("https://example.invalid/42", &node));
    g_assert_cmpuint (node, ==, 7);
}

static void
 test_public_gobject_types (void)
{
    g_assert_true (g_type_is_a (QRTR_TYPE_BUS, G_TYPE_OBJECT));
    g_assert_true (g_type_is_a (QRTR_TYPE_NODE, G_TYPE_OBJECT));
    g_assert_true (g_type_is_a (QRTR_TYPE_CLIENT, G_TYPE_OBJECT));
}

int
main (int argc, char **argv)
{
    g_test_init (&argc, &argv, NULL);
    g_test_add_func ("/libqrtr/uri/zero", test_uri_for_node_zero);
    g_test_add_func ("/libqrtr/uri/round-trip", test_uri_round_trip);
    g_test_add_func ("/libqrtr/uri/reject-invalid", test_uri_reject_invalid);
    g_test_add_func ("/libqrtr/gobject/public-types", test_public_gobject_types);
    return g_test_run ();
}
