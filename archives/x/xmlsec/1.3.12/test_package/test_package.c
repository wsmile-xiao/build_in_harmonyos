#include <stdio.h>
#include <xmlsec/xmlsec.h>

int main(void) {
    if (xmlSecInit() < 0) {
        printf("CHECK-FAIL: init\n");
        return 1;
    }
    printf("CHECK-OK: init\n");
    xmlSecShutdown();
    printf("CHECK-OK: shutdown\n");
    return 0;
}
