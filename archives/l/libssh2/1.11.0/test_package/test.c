#include <libssh2.h>
#include <stdio.h>

int main(void) {
    const char *version = libssh2_version(LIBSSH2_VERSION_NUM);
    LIBSSH2_SESSION *session;

    if (version == NULL) {
        fprintf(stderr, "libssh2_version returned NULL\n");
        return 1;
    }

    if (libssh2_init(0) != 0) {
        fprintf(stderr, "libssh2_init failed\n");
        return 1;
    }

    session = libssh2_session_init_ex(NULL, NULL, NULL, NULL);
    if (session == NULL) {
        fprintf(stderr, "libssh2_session_init_ex failed\n");
        libssh2_exit();
        return 1;
    }

    libssh2_session_set_timeout(session, 1234);
    if (libssh2_session_get_timeout(session) != 1234) {
        fprintf(stderr, "session timeout round-trip failed\n");
        libssh2_session_free(session);
        libssh2_exit();
        return 1;
    }

    if (libssh2_session_free(session) != 0) {
        fprintf(stderr, "libssh2_session_free failed\n");
        libssh2_exit();
        return 1;
    }

    libssh2_exit();
    printf("libssh2 consumer probe ok: %s\n", version);
    return 0;
}
