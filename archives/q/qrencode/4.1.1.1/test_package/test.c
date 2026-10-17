#include <stdio.h>
#include <stdlib.h>
#include <qrencode.h>

int main(void) {
    const char payload[] = "Hello OHOS";
    QRcode *qr = QRcode_encodeString(payload, 0, QR_ECLEVEL_L, QR_MODE_8, 1);
    if (qr == NULL) {
        fprintf(stderr, "Failed to encode QR code\n");
        return 1;
    }
    if (qr->width < 21 || qr->width % 4 != 1 || qr->data == NULL) {
        fprintf(stderr, "Invalid QR matrix: width=%d\n", qr->width);
        QRcode_free(qr);
        return 1;
    }
    size_t black_modules = 0;
    for (int i = 0; i < qr->width * qr->width; ++i) {
        black_modules += (qr->data[i] & 1u) != 0;
    }
    if (black_modules == 0) {
        fprintf(stderr, "QR matrix has no populated modules\n");
        QRcode_free(qr);
        return 1;
    }
    printf("QR code generated: %dx%d for %s\n", qr->width, qr->width, payload);
    QRcode_free(qr);
    printf("test qrencode upstream 4.1.1 (Conan 4.1.1.1): OK\n");
    return 0;
}
