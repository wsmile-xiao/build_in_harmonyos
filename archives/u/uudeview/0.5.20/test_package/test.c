#include <stdio.h>
#include <uudeview.h>

int main(void) {
    /* Test that the uulib API is accessible */
    int rc = UUInitialize();
    if (rc != UURET_OK) {
        printf("uudeview 0.5.20: UUInitialize failed with code %d\n", rc);
        UUCleanUp();
        return 1;
    }
    UUCleanUp();
    printf("uudeview 0.5.20: uulib API test OK\n");
    return 0;
}
