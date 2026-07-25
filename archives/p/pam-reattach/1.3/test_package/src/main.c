#include <errno.h>
#include <stdio.h>
#include <reattach.h>

int main(void)
{
    int rc = reattach_aqua(0);
    if (rc != ENOTSUP) {
        fprintf(stderr, "expected ENOTSUP from OHOS reattach_aqua stub, got %d\n", rc);
        return 1;
    }
    return 0;
}
