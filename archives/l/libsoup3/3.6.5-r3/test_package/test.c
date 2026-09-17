/* test_package real API smoke test for libsoup3 3.6.5-r3.
 *
 * libsoup 3.x removed the libsoup2 `SoupURI`/`soup_uri_new` API; URIs are
 * GLib GUri. Exercises real libsoup3 API:
 *   1. SoupMessage creation (soup_message_new)
 *   2. SoupSession creation (soup_session_new)
 *   3. GUri host parsing (used by libsoup, g_uri_parse from GLib)
 * Assertions counted: 3 (message non-NULL, session non-NULL, host match) +
 * GObject unref no-crash.
 */
#include <glib.h>
#include <libsoup/soup.h>

#include <stdio.h>
#include <string.h>

int main(void) {
    int failures = 0;

    /* 1. libsoup3 URI handling: parse with GLib GUri, verify host */
    GUri *uri = g_uri_parse("https://example.com/path?q=1", G_URI_FLAGS_NONE, NULL);
    if (uri == NULL) {
        fprintf(stderr, "FAIL: g_uri_parse returned NULL\n");
        return 1;
    }
    const char *host = g_uri_get_host(uri);
    if (host == NULL || strcmp(host, "example.com") != 0) {
        fprintf(stderr, "FAIL: g_uri_get_host=%s (expected example.com)\n",
                host ? host : "(null)");
        failures++;
    }
    /* copy host before unref (g_uri_unref frees it) */
    char host_buf[256];
    host_buf[0] = '\0';
    if (host != NULL) {
        strncpy(host_buf, host, sizeof(host_buf) - 1);
        host_buf[sizeof(host_buf) - 1] = '\0';
    }

    /* 2. libsoup3 SoupMessage creation */
    SoupMessage *msg = soup_message_new("GET", "https://example.com/");
    if (msg == NULL) {
        fprintf(stderr, "FAIL: soup_message_new returned NULL\n");
        failures++;
    }

    /* 3. libsoup3 SoupSession creation */
    SoupSession *session = soup_session_new();
    if (session == NULL) {
        fprintf(stderr, "FAIL: soup_session_new returned NULL\n");
        failures++;
    }

    if (msg != NULL)
        g_object_unref(msg);
    if (session != NULL) {
        soup_session_abort(session);
        g_object_unref(session);
    }
    if (uri != NULL)
        g_uri_unref(uri);

    if (failures > 0) {
        fprintf(stderr, "libsoup3 test FAILED (%d failure(s))\n", failures);
        return 1;
    }

    printf("test libsoup3 3.6.5-r3: OK (host=%s, session+message ok)\n", host_buf);
    return 0;
}
