#include <libsigrokdecode/libsigrokdecode.h>
#include <stdio.h>

int main(void)
{
    int ret = srd_init(NULL);
    if (ret != SRD_OK) {
        fprintf(stderr, "srd_init failed: %d\n", ret);
        return 1;
    }
    ret = srd_decoder_load("i2c");
    if (ret != SRD_OK) {
        fprintf(stderr, "srd_decoder_load(i2c) failed: %d\n", ret);
        srd_exit();
        return 2;
    }
    srd_exit();
    return 0;
}
