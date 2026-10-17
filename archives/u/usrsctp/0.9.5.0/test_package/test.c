/*
 * test_usrsctp — Conan test_package consumer test (R34: must actually use
 * the packaged API). Initializes the usrsctp library stack, creates an
 * endpoint socket, binds it (a real libusrsctp entry point exercised) and
 * shuts the stack down.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <arpa/inet.h>
#include <sys/socket.h>

#include <usrsctp.h>

int main(void) {
    struct socket *sock;
    struct sockaddr_in addr;
    int rc;

    usrsctp_init(0, NULL, NULL);
    usrsctp_sysctl_set_sctp_sendspace(65536);

    sock = usrsctp_socket(AF_INET, SOCK_STREAM, IPPROTO_SCTP, NULL, NULL,
                          0, NULL);
    if (sock == NULL) {
        fprintf(stderr, "usrsctp_socket failed\n");
        usrsctp_finish();
        return 1;
    }
    printf("usrsctp_socket OK\n");

    memset(&addr, 0, sizeof(addr));
    addr.sin_family = AF_INET;
    addr.sin_port = htons(9899);
    addr.sin_addr.s_addr = htonl(INADDR_ANY);
    rc = usrsctp_bind(sock, (struct sockaddr *)&addr, sizeof(addr));
    printf("usrsctp_bind rc=%d\n", rc);

    usrsctp_close(sock);
    usrsctp_finish();
    printf("usrsctp 0.9.5.0 test_package: OK\n");
    return 0;
}
