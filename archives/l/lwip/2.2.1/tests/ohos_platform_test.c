/*
 * lwIP HarmonyOS PC (aarch64) platform-specific test.
 *
 * Verifies that the lwIP stack initializes and its core raw-API resources
 * (TCP/UDP PCBs, pbufs, netif) work correctly when built for HarmonyOS PC.
 * Uses only public lwIP headers and public raw API.
 */
#include <stdio.h>
#include <string.h>
#include "lwip/init.h"
#include "lwip/tcp.h"
#include "lwip/udp.h"
#include "lwip/pbuf.h"
#include "lwip/netif.h"
#include "lwip/ip_addr.h"

/* Minimal loopback-style netif used to exercise netif_add()/netif_input() */
static struct netif ohos_test_netif;

static err_t
ohos_test_netif_init(struct netif *netif)
{
  netif->name[0] = 'o';
  netif->name[1] = 's';
  netif->output = NULL;      /* raw API tests do not send */
  netif->mtu = 1500;
  netif->flags = NETIF_FLAG_UP | NETIF_FLAG_LINK_UP;
  return ERR_OK;
}

int main(void)
{
  int failures = 0;
  struct tcp_pcb *tpcb;
  struct udp_pcb *upcb;
  struct pbuf *pb;
  ip4_addr_t ipaddr, netmask, gw;

  /* 1. stack initialization */
  lwip_init();
  printf("[OHOS] lwip_init OK (version %d.%d.%d)\n",
         LWIP_VERSION_MAJOR, LWIP_VERSION_MINOR, LWIP_VERSION_REVISION);

  /* 2. raw-API resource allocation */
  tpcb = tcp_new();
  if (tpcb == NULL) { printf("[OHOS] FAIL: tcp_new\n"); failures++; }
  else { printf("[OHOS] tcp_new OK (pcb=%p)\n", (void *)tpcb); tcp_abort(tpcb); }

  upcb = udp_new();
  if (upcb == NULL) { printf("[OHOS] FAIL: udp_new\n"); failures++; }
  else { printf("[OHOS] udp_new OK (pcb=%p)\n", (void *)upcb); udp_remove(upcb); }

  /* 3. pbuf alloc/free */
  pb = pbuf_alloc(PBUF_TRANSPORT, 512, PBUF_RAM);
  if (pb == NULL) { printf("[OHOS] FAIL: pbuf_alloc\n"); failures++; }
  else {
    memset(pb->payload, 0xAB, 16);
    printf("[OHOS] pbuf_alloc OK (len=%u, tot_len=%u)\n",
           (unsigned)pb->len, (unsigned)pb->tot_len);
    pbuf_free(pb);
  }

  /* 4. netif add/remove with a minimal OHOS netif driver */
  IP4_ADDR(&ipaddr, 10, 0, 2, 1);
  IP4_ADDR(&netmask, 255, 255, 255, 0);
  IP4_ADDR(&gw, 10, 0, 2, 254);
  if (netif_add(&ohos_test_netif, &ipaddr, &netmask, &gw, NULL,
                ohos_test_netif_init, NULL) == NULL) {
    printf("[OHOS] FAIL: netif_add\n"); failures++;
  } else {
    netif_set_up(&ohos_test_netif);
    printf("[OHOS] netif_add OK (index=%u, %s)\n",
           (unsigned)ohos_test_netif.num, ip4addr_ntoa(ip_2_ip4(&ohos_test_netif.ip_addr)));
    netif_remove(&ohos_test_netif);
  }

  if (failures == 0) {
    printf("[OHOS] ALL lwIP platform tests PASSED\n");
    return 0;
  }
  printf("[OHOS] %d FAILURE(S)\n", failures);
  return 1;
}
