#include <stdio.h>
#include <string.h>
#include <htslib/hts.h>
#include <htslib/sam.h>

int main(void) {
    const char *version = hts_version();
    if (version == NULL || strlen(version) == 0) {
        fprintf(stderr, "hts_version returned an empty value\n");
        return 1;
    }

    sam_hdr_t *hdr = sam_hdr_init();
    if (hdr == NULL) {
        fprintf(stderr, "sam_hdr_init failed\n");
        return 1;
    }
    sam_hdr_destroy(hdr);

    printf("htslib version: %s\n", version);
    return 0;
}
