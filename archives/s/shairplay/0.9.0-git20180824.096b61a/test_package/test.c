#include <shairplay/dnssd.h>
#include <stdio.h>

int main(void)
{
    int error = -1;
    dnssd_t *service = dnssd_init(&error);
    if (service != 0) {
        if (error != DNSSD_ERROR_NOERROR)
            return 1;
        dnssd_destroy(service);
        puts("shairplay DNS-SD consumer: PASS");
        return 0;
    }
    /* A DNS-SD runtime is optional; absence must be reported explicitly. */
    if (error == DNSSD_ERROR_LIBNOTFOUND ||
        error == DNSSD_ERROR_PROCNOTFOUND) {
        puts("shairplay DNS-SD consumer: PASS");
        return 0;
    }
    return 2;
}
