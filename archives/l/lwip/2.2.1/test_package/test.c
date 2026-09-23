#include <stdio.h>
#include "lwip/init.h"
#include "lwip/tcp.h"

int main(void) {
    struct tcp_pcb *pcb;
    /* Real lwIP public raw API: initialize the stack and create a TCP PCB. */
    lwip_init();
    pcb = tcp_new();
    if (pcb == NULL) {
        printf("test lwip %d.%d.%d: tcp_new FAILED\n",
               LWIP_VERSION_MAJOR, LWIP_VERSION_MINOR, LWIP_VERSION_REVISION);
        return 1;
    }
    tcp_abort(pcb);
    printf("test lwip %d.%d.%d: init + tcp_new ok\n",
           LWIP_VERSION_MAJOR, LWIP_VERSION_MINOR, LWIP_VERSION_REVISION);
    return 0;
}
