/* Consumer test for libpolkit-agent-1 (upstream module polkit-agent-1).
 *
 * The recipe polkit/124.1 ships the agent library that polkit/124 skipped in
 * libs-only mode, so this test must prove that a downstream agent (e.g.
 * lomiri-polkit-agent) can actually build and use it:
 *   - the public headers install under <polkit-1>/polkitagent/ and pull in the
 *     generated enum types header (meson mkenums_simple output),
 *   - the GObject types of the agent library resolve from the shared library
 *     and the class hierarchy is the upstream one,
 *   - the types can be instantiated through the plain GObject constructor.
 *
 * PolkitAgentTextListener's GInitable constructor (polkit_agent_text_listener_new)
 * opens the controlling terminal and therefore cannot succeed in a CI sandbox
 * without a tty; the type is instantiated with g_object_new() instead, which
 * exercises type registration, class init and the GObject vtable without
 * requiring a terminal, a D-Bus system bus or a running polkitd.
 */
#define POLKIT_AGENT_I_KNOW_API_IS_SUBJECT_TO_CHANGE 1
#include <polkitagent/polkitagent.h>
#include <glib.h>
#include <stdio.h>

int
main (void)
{
    GType listener_type = polkit_agent_listener_get_type ();
    GType text_listener_type = polkit_agent_text_listener_get_type ();
    gpointer obj;

    if (listener_type == 0 || text_listener_type == 0) {
        g_printerr ("agent GTypes are not registered (library not loaded?)\n");
        return 1;
    }

    if (g_strcmp0 (g_type_name (listener_type), "PolkitAgentListener") != 0) {
        g_printerr ("unexpected type name for the listener base: %s\n",
                    g_type_name (listener_type));
        return 1;
    }
    if (g_strcmp0 (g_type_name (text_listener_type), "PolkitAgentTextListener") != 0) {
        g_printerr ("unexpected type name for the text listener: %s\n",
                    g_type_name (text_listener_type));
        return 1;
    }
    if (!g_type_is_a (text_listener_type, listener_type)) {
        g_printerr ("PolkitAgentTextListener is not a PolkitAgentListener subclass\n");
        return 1;
    }

    obj = g_object_new (POLKIT_AGENT_TYPE_TEXT_LISTENER, NULL);
    if (obj == NULL) {
        g_printerr ("g_object_new(POLKIT_AGENT_TYPE_TEXT_LISTENER) returned NULL\n");
        return 1;
    }
    if (!G_IS_OBJECT (obj) ||
        !POLKIT_AGENT_IS_LISTENER (obj) ||
        !POLKIT_AGENT_IS_TEXT_LISTENER (obj)) {
        g_printerr ("instantiated object does not match the agent types\n");
        g_object_unref (obj);
        return 1;
    }

    g_print ("polkit-agent-1 OK: listener=%s text_listener=%s instance=%p\n",
             g_type_name (listener_type),
             g_type_name (text_listener_type),
             obj);
    g_object_unref (obj);
    return 0;
}
