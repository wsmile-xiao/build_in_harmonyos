#include <stdio.h>
#include <sys/time.h>

#include <glib-object.h>
#include <glib.h>

#include <avahi-common/timeval.h>
#include <avahi-glib/glib-watch.h>
#include <avahi-gobject/ga-client.h>

static int checks;
static int passed;
static int timeout_fired;

static void check(int condition, const char *message) {
    checks++;
    if (condition) {
        passed++;
    } else {
        fprintf(stderr, "FAIL: %s\n", message);
    }
}

static void on_timeout(AvahiTimeout *timeout, void *userdata) {
    (void) timeout;
    (void) userdata;
    timeout_fired = 1;
}

int main(void) {
    GMainContext *context = g_main_context_new();
    AvahiGLibPoll *adapter = NULL;
    const AvahiPoll *poll_api = NULL;
    AvahiTimeout *timeout = NULL;
    struct timeval deadline;
    GType client_type;
    gint64 stop_at;

    check(context != NULL, "create dedicated GMainContext");

    if (context != NULL)
        adapter = avahi_glib_poll_new(context, G_PRIORITY_DEFAULT);
    check(adapter != NULL, "create AvahiGLibPoll");

    if (adapter != NULL)
        poll_api = avahi_glib_poll_get(adapter);
    check(poll_api != NULL, "get AvahiPoll API");

    check(poll_api != NULL &&
              poll_api->timeout_new != NULL &&
              poll_api->timeout_free != NULL,
          "timeout callbacks are available");

    if (poll_api != NULL && poll_api->timeout_new != NULL) {
        avahi_elapse_time(&deadline, 5, 0);
        timeout = poll_api->timeout_new(
            poll_api, &deadline, on_timeout, NULL);
    }
    check(timeout != NULL, "create Avahi timeout");

    if (context != NULL && timeout != NULL) {
        stop_at = g_get_monotonic_time() + 2 * G_TIME_SPAN_SECOND;
        do {
            while (g_main_context_iteration(context, FALSE))
                ;
            if (!timeout_fired)
                g_usleep(1000);
        } while (!timeout_fired && g_get_monotonic_time() < stop_at);
    }
    check(timeout_fired, "dispatch timeout through GLib context");

    if (timeout != NULL && poll_api != NULL)
        poll_api->timeout_free(timeout);

    client_type = ga_client_get_type();
    check(client_type != G_TYPE_INVALID, "register GaClient GType");
    check(g_type_is_a(client_type, G_TYPE_OBJECT),
          "GaClient derives from GObject");

    if (adapter != NULL)
        avahi_glib_poll_free(adapter);
    if (context != NULL)
        g_main_context_unref(context);

    printf(
        "HMBS_TEST_PACKAGE_RESULT="
        "{\"executed\":true,\"passed\":%s,"
        "\"command\":\"test_avahi_glib\","
        "\"discovered\":%d,\"passedCount\":%d}\n",
        checks == passed ? "true" : "false", checks, passed);

    return checks == passed && checks == 8 ? 0 : 1;
}
