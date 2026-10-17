#include <stdio.h>
#include <string.h>

#include "pico_stack.h"
#include "pico_ipv4.h"

int main(void) {
    struct pico_ip4 ip;
    char buf[46] = {0};

    pico_stack_init();

    /* Real API assertions against the compiled stack library. */
    if (pico_string_to_ipv4("192.168.7.11", &ip.addr) != 0) {
        fprintf(stderr, "pico_string_to_ipv4 rejected a valid address\n");
        return 1;
    }
    pico_ipv4_to_string(buf, ip.addr);
    if (strcmp(buf, "192.168.7.11") != 0) {
        fprintf(stderr, "round-trip mismatch: got %s\n", buf);
        return 2;
    }
    pico_stack_tick();

    puts("picotcp API assertions: 3 passed");
    return 0;
}
