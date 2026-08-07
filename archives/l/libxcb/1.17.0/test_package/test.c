/* libxcb 1.17.0 consumer link + API smoke test.
 *
 * Exercises the public XCB connection-lifecycle path:
 *   xcb_connect() -> xcb_connection_has_error() -> xcb_disconnect()
 * and a couple of pre-defined protocol constants. Without an X server
 * running on :99 the connect must return a non-NULL handle flagged with
 * a connection error (this is the documented contract for xcb_connect).
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <xcb/xcb.h>

int main(void) {
    /* 1. Protocol-version constants from <xcb/xcb.h>. */
    if (X_PROTOCOL != 11) {
        fprintf(stderr, "X_PROTOCOL != 11 (got %d)\n", X_PROTOCOL);
        return 1;
    }
    if (X_PROTOCOL_REVISION != 0) {
        fprintf(stderr, "X_PROTOCOL_REVISION != 0 (got %d)\n", X_PROTOCOL_REVISION);
        return 2;
    }
    if (X_TCP_PORT != 6000) {
        fprintf(stderr, "X_TCP_PORT != 6000 (got %d)\n", X_TCP_PORT);
        return 3;
    }

    /* 2. xcb_connect() with a display name that no X server is listening on.
     *    Per the API contract (xcb.h:565), xcb_connect() ALWAYS returns a
     *    non-NULL handle; callers must inspect xcb_connection_has_error().
     */
    int screen = -1;
    xcb_connection_t *c = xcb_connect(":99", &screen);
    if (c == NULL) {
        fprintf(stderr, "xcb_connect returned NULL (forbidden by API contract)\n");
        return 4;
    }

    /* 3. No server on :99 -> has_error() must report a non-zero status.
     *    The numeric value is platform-specific; we only assert non-zero.
     */
    int err = xcb_connection_has_error(c);
    if (err == 0) {
        fprintf(stderr, "xcb_connection_has_error returned 0 with no server on :99\n");
        xcb_disconnect(c);
        return 5;
    }

    /* 4. xcb_disconnect() must be safe to call on an errored connection. */
    xcb_disconnect(c);

    /* 5. NULL is also documented to be tolerated by xcb_disconnect(). */
    xcb_disconnect(NULL);

    /* 6. Touch the still-exported xcb_parse_display helper.
     *    int xcb_parse_display(const char *name, char **host, int *display, int *screen);
     *    Returns 0 on parse error (NULL name falls back to getenv("DISPLAY");
     *    if DISPLAY is unset or malformed, that yields 0). With all output
     *    pointers NULL, the helper must not crash.
     */
    int parsed = xcb_parse_display(NULL, NULL, NULL, NULL);
    if (parsed != 0) {
        fprintf(stderr, "xcb_parse_display with no DISPLAY env must return 0 (got %d)\n", parsed);
        return 6;
    }

    if (printf("libxcb api smoke ok\n") < 0) {
        return 7;
    }
    return 0;
}