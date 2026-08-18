#include <stdio.h>
#include <nghttp2/nghttp2.h>

int main(void) {
    /* Verify nghttp2 library is linkable and functional */
    const char *ver = nghttp2_version(0);
    if (ver == NULL) {
        fprintf(stderr, "nghttp2_version returned NULL\n");
        return 1;
    }
    printf("nghttp2 version: %s\n", ver);

    /* Initialize a session to verify core API works */
    nghttp2_session *session;
    nghttp2_session_callbacks *callbacks;
    int rv = nghttp2_session_callbacks_new(&callbacks);
    if (rv != 0) {
        fprintf(stderr, "nghttp2_session_callbacks_new failed: %d\n", rv);
        return 1;
    }
    rv = nghttp2_session_client_new(&session, callbacks, NULL);
    if (rv != 0) {
        fprintf(stderr, "nghttp2_session_client_new failed: %d\n", rv);
        nghttp2_session_callbacks_del(callbacks);
        return 1;
    }
    nghttp2_session_callbacks_del(callbacks);
    nghttp2_session_del(session);

    printf("nghttp2 test: OK\n");
    return 0;
}
