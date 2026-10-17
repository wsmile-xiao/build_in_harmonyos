/*
 * lwIP consumer test — simulates an upstream business component/application
 * that uses lwIP only through its installed public headers, public API,
 * normal link target and runtime artifacts (as a third-party consumer would).
 *
 * Uses: lwip/init.h (lwip_init), lwip/tcp.h (tcp_new/tcp_bind/tcp_abort),
 *       lwip/udp.h (udp_new/udp_bind/udp_remove), lwip/pbuf.h (pbuf_alloc/free)
 * Only public headers from the installed package include/ dir are included.
 */
#include <stdio.h>
#include <string.h>
#include "lwip/init.h"
#include "lwip/tcp.h"
#include "lwip/udp.h"
#include "lwip/pbuf.h"
#include "lwip/ip_addr.h"

int main(void)
{
  struct tcp_pcb *t;
  struct udp_pcb *u;
  struct pbuf *pb;
  ip_addr_t local_ip;
  int rc = 0;

  /* initialize the lwIP stack (public API) */
  lwip_init();

  /* TCP listener socket creation + bind (public API) */
  t = tcp_new();
  if (t == NULL) { printf("[consumer] FAIL: tcp_new\n"); return 1; }
  IP_ADDR4(&local_ip, 0, 0, 0, 0);
  if (tcp_bind(t, &local_ip, 8080) != ERR_OK) {
    printf("[consumer] FAIL: tcp_bind\n"); rc = 1;
  } else {
    printf("[consumer] tcp_bind 0.0.0.0:8080 OK\n");
  }
  tcp_abort(t);

  /* UDP endpoint + bind (public API) */
  u = udp_new();
  if (u == NULL) { printf("[consumer] FAIL: udp_new\n"); return 1; }
  IP_ADDR4(&local_ip, 0, 0, 0, 0);
  if (udp_bind(u, &local_ip, 5353) != ERR_OK) {
    printf("[consumer] FAIL: udp_bind\n"); rc = 1;
  } else {
    printf("[consumer] udp_bind 0.0.0.0:5353 OK\n");
  }
  udp_remove(u);

  /* pbuf data buffer (public API) */
  pb = pbuf_alloc(PBUF_TRANSPORT, 100, PBUF_RAM);
  if (pb == NULL) { printf("[consumer] FAIL: pbuf_alloc\n"); return 1; }
  memset(pb->payload, 0, pb->len);
  pbuf_free(pb);

  printf("[consumer] lwIP %d.%d.%d consumer validation PASSED\n",
         LWIP_VERSION_MAJOR, LWIP_VERSION_MINOR, LWIP_VERSION_REVISION);
  return rc;
}
