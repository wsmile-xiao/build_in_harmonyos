/*
 * Consumer test for the installed libdsme package.
 *
 * Exercises the public dsmesock protocol, message and alarm-limit APIs of
 * the installed library against a mock DSME peer.  The platform-specific
 * part is the abstract AF_UNIX socket name ("@..."): OHOS denies creating
 * unix sockets on the file system (HMDFS bind() returns EPERM and /tmp is
 * read-only), so this consumer verifies that dsmesock_connect() really
 * reaches a listener bound to an abstract name, that the message framing
 * (including extra payload) survives a two-way round trip, that peer
 * credentials are queryable, and that connecting to a nonexistent
 * endpoint fails cleanly instead of aborting.
 */

#ifndef _GNU_SOURCE
#define _GNU_SOURCE
#endif

#include <dsme/alarm_limit.h>
#include <dsme/messages.h>
#include <dsme/protocol.h>
#include <dsme/state.h>

#include <errno.h>
#include <stddef.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/un.h>
#include <unistd.h>

/* assert() would be compiled out by Release builds (-DNDEBUG); keep a hard
 * check so the test can never silently pass. */
#define CHECK(EXPR)                                                     \
    do {                                                                \
        if (!(EXPR)) {                                                  \
            fprintf(stderr, "FAIL %s:%d: %s\n",                         \
                    __FILE__, __LINE__, #EXPR);                         \
            exit(EXIT_FAILURE);                                         \
        }                                                               \
    } while (0)

static void test_alarm_limit_api(void)
{
    CHECK(dsme_snooze_timeout_in_seconds() == 120);
}

static void test_message_api(void)
{
    dsmemsg_generic_t *message = DSME_MSG_NEW(DSM_MSGTYPE_GET_VERSION);

    CHECK(message != NULL);
    CHECK(dsmemsg_id(message) == DSM_MSGTYPE_GET_VERSION_ID_);
    CHECK(dsmemsg_size(message) == sizeof *message);
    CHECK(dsmemsg_line_size(message) == sizeof *message);
    CHECK(dsmemsg_extra_size(message) == 0);
    CHECK(strcmp(dsmemsg_name(message), "GET_VERSION") == 0);
    free(message);

    message = DSME_MSG_NEW_WITH_EXTRA(DSM_MSGTYPE_DSME_VERSION, 8);
    CHECK(message != NULL);
    CHECK(dsmemsg_id(message) == DSM_MSGTYPE_DSME_VERSION_ID_);
    CHECK(dsmemsg_extra_size(message) == 8);
    CHECK(dsmemsg_line_size(message) == sizeof *message + 8);
    CHECK(dsmemsg_extra_data(message) != NULL);
    free(message);

    message = dsmemsg_new(42, sizeof *message, 0);
    CHECK(message != NULL);
    CHECK(strcmp(dsmemsg_id_name(42), "UNKNOWN_0000002a") == 0);
    CHECK(strcmp(dsmemsg_name(message), "UNKNOWN_0000002a") == 0);
    CHECK(strcmp(dsmemsg_name(NULL), "NULL_MESSAGE") == 0);
    free(message);
}

static void test_connect_failure(void)
{
    /* Negative control: no listener on this abstract name. */
    setenv("DSME_SOCKFILE", "@libdsme-no-such-endpoint", 1);
    CHECK(dsmesock_connect() == NULL);
}

static dsmemsg_generic_t *receive_with_timeout(dsmesock_connection_t *connection)
{
    dsmemsg_generic_t *message = NULL;

    for (int i = 0; i < 50 && message == NULL; ++i) {
        usleep(100000); /* 100 ms */
        message = dsmesock_receive(connection);
    }
    return message;
}

static void test_abstract_socket_round_trip(void)
{
    const char *endpoint = "@libdsme-consumer-test";
    const char extra[] = "libdsme-consumer-extra";

    int listener = socket(PF_UNIX, SOCK_STREAM, 0);
    CHECK(listener != -1);

    struct sockaddr_un address;
    memset(&address, 0, sizeof address);
    address.sun_family = AF_UNIX;
    size_t name_length = strlen(endpoint + 1);
    CHECK(name_length + 1 < sizeof address.sun_path);
    memcpy(address.sun_path + 1, endpoint + 1, name_length);
    socklen_t address_length = (socklen_t)(
        offsetof(struct sockaddr_un, sun_path) + 1 + name_length);
    CHECK(bind(listener, (const struct sockaddr *)&address, address_length) == 0);
    CHECK(listen(listener, 1) == 0);

    /* dsmesock_connect() must resolve the abstract name and connect. */
    setenv("DSME_SOCKFILE", endpoint, 1);
    dsmesock_connection_t *client = dsmesock_connect();
    CHECK(client != NULL);

    int server_fd = accept(listener, NULL, NULL);
    CHECK(server_fd != -1);
    dsmesock_connection_t *server = dsmesock_init(server_fd);
    CHECK(server != NULL);

    /* client -> server: state query. */
    DSM_MSGTYPE_STATE_QUERY query = DSME_MSG_INIT(DSM_MSGTYPE_STATE_QUERY);
    CHECK(dsmesock_send(client, &query) > 0);

    dsmemsg_generic_t *received = receive_with_timeout(server);
    CHECK(received != NULL);
    CHECK(dsmemsg_id(received) == DSM_MSGTYPE_STATE_QUERY_ID_);
    free(received);

    /* server -> client: denied indication with an extra payload. */
    DSM_MSGTYPE_STATE_REQ_DENIED_IND denied =
        DSME_MSG_INIT(DSM_MSGTYPE_STATE_REQ_DENIED_IND);
    denied.state = DSME_STATE_TEST;
    CHECK(dsmesock_send_with_extra(server, &denied, sizeof extra, extra) > 0);

    dsmemsg_generic_t *reply = receive_with_timeout(client);
    CHECK(reply != NULL);
    CHECK(dsmemsg_id(reply) == DSM_MSGTYPE_STATE_REQ_DENIED_IND_ID_);
    CHECK(dsmemsg_extra_size(reply) == sizeof extra);
    DSM_MSGTYPE_STATE_REQ_DENIED_IND *cast =
        DSMEMSG_CAST(DSM_MSGTYPE_STATE_REQ_DENIED_IND, reply);
    CHECK(cast != NULL);
    CHECK(cast->state == DSME_STATE_TEST);
    CHECK(strcmp((const char *)DSMEMSG_EXTRA(cast), extra) == 0);
    free(reply);

    /* Peer credentials of the accepted connection must be queryable. */
    CHECK(dsmesock_getucred(server) != NULL);

    dsmesock_close(client);
    dsmesock_close(server);
    close(listener);
}

int main(void)
{
    test_alarm_limit_api();
    test_message_api();
    test_connect_failure();
    test_abstract_socket_round_trip();

    printf("libdsme consumer test: OK\n");
    return 0;
}
