/* test_package real API smoke test for libsoup 2.74.3.
 *
 * Exercises real libsoup2 API:
 *   1. SoupURI creation and host parsing (soup_uri_new)
 *   2. SoupMessage creation (soup_message_new)
 *   3. SoupSession creation (soup_session_new)
 * Assertions: URI non-NULL + host match + message non-NULL + session non-NULL.
 */
#include <glib.h>
#include <libsoup/soup.h>

#include <stdio.h>
#include <string.h>

int main(void) {
    int failures = 0;

    /* 1. libsoup2 SoupURI creation and host parsing */
    SoupURI *uri = soup_uri_new("https://example.com/path?q=1");
    if (uri == NULL) {
        fprintf(stderr, "FAIL: soup_uri_new returned NULL\n");
        failures++;
    } else {
        const char *host = soup_uri_get_host(uri);
        if (host == NULL || strcmp(host, "example.com") != 0) {
            fprintf(stderr, "FAIL: soup_uri_get_host=%s (expected example.com)\n",
                    host ? host : "(null)");
            failures++;
        }
    }

    /* 2. libsoup2 SoupMessage creation */
    SoupMessage *msg = soup_message_new("GET", "https://example.com/");
    if (msg == NULL) {
        fprintf(stderr, "FAIL: soup_message_new returned NULL\n");
        failures++;
    }

    /* 3. libsoup2 SoupSession creation */
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
        soup_uri_free(uri);

    if (failures > 0) {
        fprintf(stderr, "libsoup test FAILED (%d failure(s))\n", failures);
        return 1;
    }

    printf("test libsoup 2.74.3: OK (URI+message+session ok)\n");
    return 0;
}
