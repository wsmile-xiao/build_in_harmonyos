/* libxcb 1.16 consumer link + public API smoke test.
 *
 * The test avoids connecting to a real X server. It checks display parsing
 * and links a generated core protocol extension symbol from xcb-proto XML.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <xcb/bigreq.h>
#include <xcb/xcb.h>

static int expect_parse(const char *display, const char *host, int number, int screen) {
    char *got_host = NULL;
    int got_number = -1;
    int got_screen = -1;
    int ok = xcb_parse_display(display, &got_host, &got_number, &got_screen);
    if (!ok) {
        fprintf(stderr, "xcb_parse_display(%s) failed\n", display);
        free(got_host);
        return 1;
    }
    if (strcmp(got_host, host) != 0 || got_number != number || got_screen != screen) {
        fprintf(stderr, "unexpected parse result: host=%s display=%d screen=%d\n",
                got_host, got_number, got_screen);
        free(got_host);
        return 2;
    }
    free(got_host);
    return 0;
}

int main(void) {
    if (expect_parse(":7.3", "", 7, 3) != 0) {
        return 1;
    }
    if (expect_parse("example.org:2", "example.org", 2, 0) != 0) {
        return 2;
    }
    printf("bigreq extension symbol: %p\n", (void *)&xcb_big_requests_id);
    printf("libxcb api smoke ok\n");
    return 0;
}
