/* test_package/test_dyad.c — dyad consumer test: TCP socket loopback.
 *
 * dyad is a single-selector (select) event-loop TCP library. This test
 * exercises the full consumer path on OHOS with no external network
 * access (127.0.0.1 loopback works inside the OHOS sandbox):
 *
 *   1  dyad_getVersion() banner matches the master-tip release string
 *   2  dyad_listenEx() binds 127.0.0.1 with port=0 (kernel-assigned)
 *   3  the ephemeral port is observable via dyad_getPort()
 *   4  server stream reaches DYAD_STATE_LISTENING
 *   5  dyad_connect() to the loopback listener returns 0
 *   6  client CONNECT event fires
 *   7  server ACCEPT event fires
 *   8  client receives the greeting through the LINE event (\n stripped)
 *   9  server receives the exact client payload via DATA event
 *  10  dyad_getAddress(client) == "127.0.0.1"
 *  11  dyad_getPort(client) reports the server port (getpeername path)
 *  12  dyad_getBytesSent(client) == payload size
 *  13  dyad_getAddress(remote) == "127.0.0.1"
 *  14  dyad_getBytesReceived(remote) == payload size
 *  15  dyad_getStreamCount() == 0 after shutdown (no stream leaks)
 *
 * The program itself performs all assertions and returns non-zero when
 * any of them fails; test_package/conanfile.py runs it via self.run().
 */
#include <stdio.h>
#include <string.h>
#include "dyad.h"

static int passed = 0, failed = 0;

static void check(int cond, const char *name) {
  if (cond) { passed++; printf("PASS: %s\n", name); }
  else      { failed++; printf("FAIL: %s\n", name); }
}

/* client-side state */
static int client_connected = 0;
static char client_line[256] = "";
static int client_got_line = 0;
static char client_addr[64] = "";
static int client_peer_port = -1;

/* server-side state */
static int server_accepted = 0;
static dyad_Stream *remote = NULL;
static char remote_data[256] = "";
static int remote_got_data = 0;

static const char *kPayload = "ping-from-client";
static const char *kGreeting = "hello-client";

static void onClientConnect(dyad_Event *e) {
  client_connected = 1;
  snprintf(client_addr, sizeof(client_addr), "%s", dyad_getAddress(e->stream));
  client_peer_port = dyad_getPort(e->stream);
  dyad_write(e->stream, kPayload, (int)strlen(kPayload));
}

static void onClientLine(dyad_Event *e) {
  snprintf(client_line, sizeof(client_line), "%s", e->data);
  client_got_line = 1;
}

static void onRemoteData(dyad_Event *e) {
  if (e->size >= 0 && e->size < (int)sizeof(remote_data)) {
    memcpy(remote_data, e->data, (size_t)e->size);
    remote_data[e->size] = 0;
    remote_got_data = 1;
  }
}

static void onAccept(dyad_Event *e) {
  server_accepted = 1;
  remote = e->remote;
  dyad_addListener(e->remote, DYAD_EVENT_DATA, onRemoteData, NULL);
  dyad_writef(e->remote, "%s\n", kGreeting);
}

static void onError(dyad_Event *e) {
  printf("ERROR event: %s\n", e->msg);
}

int main(void) {
  dyad_Stream *server, *client;
  int server_port;
  double deadline;

  dyad_init();

  /* 1. version banner */
  check(strcmp(dyad_getVersion(), "0.2.1") == 0,
        "dyad_getVersion() == 0.2.1 (master-tip banner)");

  /* 2-4. server: bind loopback, kernel-assigned ephemeral port */
  server = dyad_newStream();
  dyad_addListener(server, DYAD_EVENT_ACCEPT, onAccept, NULL);
  dyad_addListener(server, DYAD_EVENT_ERROR, onError, NULL);
  check(dyad_listenEx(server, "127.0.0.1", 0, 16) == 0,
        "dyad_listenEx(127.0.0.1, port=0) succeeds");
  server_port = dyad_getPort(server);
  check(server_port > 0 && server_port < 65536,
        "kernel-assigned ephemeral port observed via dyad_getPort()");
  check(dyad_getState(server) == DYAD_STATE_LISTENING,
        "server stream is DYAD_STATE_LISTENING");

  /* 5. client: async connect to loopback */
  client = dyad_newStream();
  dyad_addListener(client, DYAD_EVENT_CONNECT, onClientConnect, NULL);
  dyad_addListener(client, DYAD_EVENT_LINE, onClientLine, NULL);
  dyad_addListener(client, DYAD_EVENT_ERROR, onError, NULL);
  check(dyad_connect(client, "127.0.0.1", server_port) == 0,
        "dyad_connect(127.0.0.1, server_port) returns 0");

  /* pump the single-thread event loop until the exchange completes */
  deadline = dyad_getTime() + 5.0;
  while (dyad_getTime() < deadline) {
    if (client_connected && server_accepted && client_got_line && remote_got_data) break;
    dyad_update();
  }

  /* 6-15. assert the full round trip */
  check(client_connected, "client CONNECT event fired on loopback");
  check(server_accepted, "server ACCEPT event fired");
  check(client_got_line && strcmp(client_line, kGreeting) == 0,
        "client LINE event delivered the greeting (newline stripped)");
  check(remote_got_data && strcmp(remote_data, kPayload) == 0,
        "server received the exact client payload");
  check(strcmp(client_addr, "127.0.0.1") == 0,
        "dyad_getAddress(client) == 127.0.0.1");
  check(client_peer_port == server_port,
        "dyad_getPort(client) reports the server port");
  check(dyad_getBytesSent(client) == (int)strlen(kPayload),
        "dyad_getBytesSent(client) == payload size");
  if (remote != NULL) {
    check(strcmp(dyad_getAddress(remote), "127.0.0.1") == 0,
          "dyad_getAddress(remote) == 127.0.0.1");
    check(dyad_getBytesReceived(remote) == (int)strlen(kPayload),
          "dyad_getBytesReceived(remote) == payload size");
  } else {
    check(0, "remote stream captured (accept callback ran)");
    check(0, "dyad_getBytesReceived(remote) == payload size");
  }

  /* orderly close and leak check */
  dyad_end(client);
  dyad_update();   /* propagate the close to the server side */
  dyad_shutdown();
  check(dyad_getStreamCount() == 0,
        "dyad_getStreamCount() == 0 after shutdown (no stream leaks)");

  printf("dyad loopback test: %d passed, %d failed\n", passed, failed);
  return (failed == 0) ? 0 : 1;
}
