#include <stdio.h>
#include <stdlib.h>
#include <ldns/ldns.h>

int main(void) {
    /* R34: Test must actually use the ldns API */
    /* Create a new rr_list to verify the library is linked and functional */
    ldns_rr_list *rr_list = ldns_rr_list_new();
    if (rr_list == NULL) {
        fprintf(stderr, "ERROR: ldns_rr_list_new() returned NULL\n");
        return 1;
    }

    /* Create a new DNS packet */
    ldns_pkt *pkt = ldns_pkt_new();
    if (pkt == NULL) {
        fprintf(stderr, "ERROR: ldns_pkt_new() returned NULL\n");
        ldns_rr_list_free(rr_list);
        return 1;
    }

    /* Verify ldns version string is accessible */
    const char *version = ldns_version();
    printf("ldns version: %s\n", version);

    /* Clean up */
    ldns_pkt_free(pkt);
    ldns_rr_list_free(rr_list);

    printf("test ldns 1.9.0: OK\n");
    return 0;
}
