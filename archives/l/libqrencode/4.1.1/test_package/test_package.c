#include <stdio.h>
#include <stdlib.h>
#include <qrencode.h>

int main(void) {
    QRcode *qr = QRcode_encodeString("Hello OHOS", 0, QR_ECLEVEL_L, QR_MODE_8, 1);
    if (qr == NULL) {
        fprintf(stderr, "Failed to encode QR code\n");
        return 1;
    }
    printf("QR code generated: %dx%d\n", qr->width, qr->width);
    QRcode_free(qr);
    printf("test libqrencode 4.1.1: OK\n");
    return 0;
}
