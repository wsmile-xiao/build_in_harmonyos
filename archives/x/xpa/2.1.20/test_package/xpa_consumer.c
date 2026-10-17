/*
 * xpa_consumer.c — behavior test for the packaged libxpa.
 *
 * An XPA server only services callbacks from inside its own event loop, so an
 * in-process XPAGet against a locally created access point deadlocks against
 * its own client call.  The access point is therefore created in a forked
 * child that runs XPAPoll while this process acts as the client — the same
 * two-process shape upstream uses for stest/ctest.
 *
 * Assertions (exit status is the number of failed assertions):
 *   1) the child's XPANew creates a real access point
 *   2) XPAGet returns the bytes produced by the send callback
 *   3) XPASet delivers a payload the receive callback sees verbatim
 *   4) cleanup: XPAFree + child exit 0
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/wait.h>

#include "xpa.h"

#define PAYLOAD   "xpa-consumer-payload-0123456789"
#define AP_CLASS  "QCXPA"
#define AP_NAME   "point"
#define TEMPLATE  AP_CLASS ":" AP_NAME

static int report_fd = -1;
static int saw_send = 0;
static int saw_recv = 0;

#ifdef ANSI_FUNC
static int
send_cb(void *client_data, void *call_data, char *paramlist, char **buf,
        size_t *len)
#else
static int
send_cb(client_data, call_data, paramlist, buf, len)
     void *client_data;
     void *call_data;
     char *paramlist;
     char **buf;
     size_t *len;
#endif
{
  (void)client_data;
  (void)call_data;
  (void)paramlist;
  *buf = strdup(PAYLOAD);
  *len = (*buf ? strlen(*buf) + 1 : 0);
  saw_send = 1;
  return 0;
}

#ifdef ANSI_FUNC
static int
recv_cb(void *client_data, void *call_data, char *paramlist, char *buf,
        size_t len)
#else
static int
recv_cb(client_data, call_data, paramlist, buf, len)
     void *client_data;
     void *call_data;
     char *paramlist;
     char *buf;
     size_t len;
#endif
{
  int ok = 0;
  (void)client_data;
  (void)call_data;
  (void)paramlist;
  if( buf != NULL && len == strlen(PAYLOAD) + 1 &&
      strcmp(buf, PAYLOAD) == 0 ){
    ok = 1;
  }
  saw_recv = ok;
  if( report_fd >= 0 ){
    if( write(report_fd, &ok, sizeof(ok)) < 0 ){
      perror("write report pipe");
    }
  }
  return 0;
}

int
main(void)
{
  int pfd[2];
  int failures = 0;
  pid_t child;

  if( pipe(pfd) != 0 ){
    perror("pipe");
    return 1;
  }

  child = fork();
  if( child < 0 ){
    perror("fork");
    return 1;
  }

  if( child == 0 ){
    /* ---- server side: own event loop, services the two callbacks ---- */
    XPA xpa;
    int i;
    close(pfd[0]);
    report_fd = pfd[1];
    xpa = XPANew(AP_CLASS, AP_NAME, "consumer test access point",
                 send_cb, NULL, NULL, recv_cb, NULL, NULL);
    if( xpa == NULL ){
      fprintf(stderr, "FAIL: XPANew returned NULL for %s\n", TEMPLATE);
      _exit(2);
    }
    /* XPAPoll(msec, maxreq): maxreq < 0 means "count pending events but process
     * nothing" (doc/pod/xpapoll.pod), so -1 here would spin 200 times without
     * ever servicing a request and the client would time out in the
     * QCXPA:point handshake.  maxreq == 0 processes all currently pending
     * requests, which is what a server loop needs. */
    for( i = 0; i < 200; i++ ){
      XPAPoll(50, 0);
      if( saw_send && saw_recv ) break;
    }
    XPAFree(xpa);
    _exit(0);
  }

  /* ---- client side ---- */
  close(pfd[1]);
  report_fd = -1;
  usleep(700000);                 /* let the child register with xpans */

  {
    char *bufs[1];
    size_t lens[1];
    char *names[1];
    char *errs[1];
    int got;

    bufs[0] = NULL;
    lens[0] = 0;
    names[0] = NULL;
    errs[0] = NULL;
    got = XPAGet(NULL, TEMPLATE, "x", NULL, bufs, lens, names, errs, 1);
    if( got != 1 || bufs[0] == NULL || strcmp(bufs[0], PAYLOAD) != 0 ){
      fprintf(stderr, "FAIL: XPAGet got=%d payload=%.40s (%s)\n",
              got, (bufs[0] ? bufs[0] : "(null)"), (errs[0] ? errs[0] : ""));
      failures++;
    } else {
      printf("OK: XPAGet round trip, %lu bytes via send callback\n",
             (unsigned long)lens[0]);
    }
    if( bufs[0] ) free(bufs[0]);
    if( errs[0] ) free(errs[0]);

    {
      char *payload = strdup(PAYLOAD);
      int len = (int)(strlen(payload) + 1);
      names[0] = NULL;
      errs[0] = NULL;
      got = XPASet(NULL, TEMPLATE, "x", NULL, payload, len, names, errs, 1);
      if( got != 1 ){
        fprintf(stderr, "FAIL: XPASet got=%d (%s)\n", got,
                (errs[0] ? errs[0] : ""));
        failures++;
      }
      if( errs[0] ) free(errs[0]);
      free(payload);
    }

    {
      int ok = 0;
      ssize_t n = read(pfd[0], &ok, sizeof(ok));
      close(pfd[0]);
      if( n != (ssize_t)sizeof(ok) || ok != 1 ){
        fprintf(stderr, "FAIL: receive callback did not observe the payload\n");
        failures++;
      } else {
        printf("OK: XPASet delivered %d bytes to the receive callback\n",
               (int)strlen(PAYLOAD) + 1);
      }
    }
  }

  {
    int st = 0;
    waitpid(child, &st, 0);
    if( !WIFEXITED(st) || WEXITSTATUS(st) != 0 ){
      fprintf(stderr, "FAIL: server child exited status=%d\n", st);
      failures++;
    }
  }

  if( failures ){
    fprintf(stderr, "CONSUMER TEST FAILED: %d assertion(s)\n", failures);
    return failures;
  }
  printf("ALL CONSUMER TESTS PASSED\n");
  return 0;
}
