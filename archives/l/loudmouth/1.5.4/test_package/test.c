/*
 * test.c — loudmouth consumer smoke test.
 *
 * Exercises real loudmouth-1 public APIs: connection object construction +
 * state query, and XML message-node construction + serialization (the core
 * XMPP stanza handling loudmouth provides on GLib).  8 assertions, each a
 * genuine loudmouth API call.
 *
 * Every assertion prints a PASS/FAIL line. At the end the program writes a
 * machine-readable counts object ({"passed":N,"failed":M}) to the path given
 * in argv[1] (if provided) and prints the same counts as a RESULT line. The
 * process exits non-zero if any assertion failed. The counts are the test's
 * own framework output — the authoritative source for the result marker.
 */
#include <loudmouth/loudmouth.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int g_passed = 0;
static int g_failed = 0;

static void check(int cond, const char *msg)
{
    if (cond) {
        printf("PASS: %s\n", msg);
        g_passed++;
    } else {
        fprintf(stderr, "FAIL: %s\n", msg);
        g_failed++;
    }
}

static void write_result_file(const char *path)
{
    FILE *f;
    if (path == NULL || *path == '\0') {
        return;
    }
    f = fopen(path, "w");
    if (f == NULL) {
        fprintf(stderr, "could not write result file: %s\n", path);
        return;
    }
    fprintf(f, "{\"passed\":%d,\"failed\":%d}\n", g_passed, g_failed);
    fclose(f);
}

int main(int argc, char **argv)
{
    LmMessage *message;
    LmMessageNode *node;
    LmMessageType type;
    gchar *xml;

    /* Connection object construction + state query (no network IO). */
    LmConnection *conn = lm_connection_new(NULL);
    check(conn != NULL, "lm_connection_new returns a connection object");
    if (conn != NULL) {
        LmConnectionState state = lm_connection_get_state(conn);
        check(state == LM_CONNECTION_STATE_CLOSED,
              "lm_connection_get_state returns CLOSED for a new connection");
        lm_connection_unref(conn);
    }

    /* 2. Build an XMPP <message> stanza and serialize it to XML. */
    message = lm_message_new(NULL, LM_MESSAGE_TYPE_MESSAGE);
    check(message != NULL, "lm_message_new creates a message object");
    if (message != NULL) {
        node = lm_message_get_node(message);
        check(node != NULL, "lm_message_get_node returns root node");
        if (node != NULL) {
            type = lm_message_get_type(message);
            check(type == LM_MESSAGE_TYPE_MESSAGE,
                  "lm_message_get_type matches the constructed message type");

            lm_message_node_set_attribute(node, "from", "conan@example.org");
            lm_message_node_set_attribute(node, "to", "service@example.org");

            xml = lm_message_node_to_string(node);
            check(xml != NULL, "lm_message_node_to_string serializes the node");
            if (xml != NULL) {
                check(strstr(xml, "<message") != NULL,
                      "serialized XML contains the <message> root element");
                check(strstr(xml, "conan@example.org") != NULL,
                      "serialized XML contains the 'from' attribute payload");
                g_free(xml);
            }
        }
        lm_message_unref(message);
    }

    printf("RESULT passed=%d failed=%d total=%d\n", g_passed, g_failed,
           g_passed + g_failed);
    write_result_file(argc > 1 ? argv[1] : NULL);

    return g_failed == 0 ? 0 : 1;
}
