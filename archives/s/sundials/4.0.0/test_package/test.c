#include <stdio.h>
#include <sundials/sundials_version.h>

int main(void) {
    char version[64];
    int ret = SUNDIALSGetVersion(version, sizeof(version));
    if (ret != 0) {
        printf("FAIL: SUNDIALSGetVersion returned %d\n", ret);
        return 1;
    }
    printf("test sundials 4.0.0: version=%s\n", version);
    printf("test sundials 4.0.0: OK\n");
    return 0;
}
