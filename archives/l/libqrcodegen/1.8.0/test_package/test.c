#include <stdio.h>
#include <string.h>
#include <stdbool.h>
#include <stdint.h>
#include "qrcodegen.h"

int main(void) {
    // Test 1: Encode text to QR code
    uint8_t qrcode[qrcodegen_BUFFER_LEN_MAX];
    uint8_t tempBuffer[qrcodegen_BUFFER_LEN_MAX];
    bool ok = qrcodegen_encodeText("Hello, world!", tempBuffer, qrcode,
        qrcodegen_Ecc_MEDIUM,
        qrcodegen_VERSION_MIN, qrcodegen_VERSION_MAX,
        qrcodegen_Mask_AUTO, true);

    if (!ok) {
        fprintf(stderr, "FAIL: qrcodegen_encodeText returned false\n");
        return 1;
    }

    // Test 2: Verify QR code size is reasonable
    int size = qrcodegen_getSize(qrcode);
    if (size < 21 || size > 177) {
        fprintf(stderr, "FAIL: QR code size %d out of expected range [21, 177]\n", size);
        return 1;
    }

    // Test 3: Verify some modules are set and some are not
    bool hasSet = false, hasUnset = false;
    for (int y = 0; y < size && (!hasSet || !hasUnset); y++) {
        for (int x = 0; x < size && (!hasSet || !hasUnset); x++) {
            if (qrcodegen_getModule(qrcode, x, y))
                hasSet = true;
            else
                hasUnset = true;
        }
    }
    if (!hasSet || !hasUnset) {
        fprintf(stderr, "FAIL: QR code modules not diverse (set=%d, unset=%d)\n", hasSet, hasUnset);
        return 1;
    }

    // Test 4: Encode binary data
    // dataAndTempbuf must be BUFFER_LEN_MAX bytes (used as both input and temp buffer)
    uint8_t dataAndTemp[qrcodegen_BUFFER_LEN_MAX] = {0x48, 0x65, 0x6C, 0x6C, 0x6F};
    uint8_t qr2[qrcodegen_BUFFER_LEN_MAX];
    ok = qrcodegen_encodeBinary(dataAndTemp, 5, qr2,
        qrcodegen_Ecc_HIGH,
        qrcodegen_VERSION_MIN, qrcodegen_VERSION_MAX,
        qrcodegen_Mask_AUTO, true);

    if (!ok) {
        fprintf(stderr, "FAIL: qrcodegen_encodeBinary returned false\n");
        return 1;
    }

    int size2 = qrcodegen_getSize(qr2);
    if (size2 < 21 || size2 > 177) {
        fprintf(stderr, "FAIL: Binary QR code size %d out of expected range\n", size2);
        return 1;
    }

    printf("All qrcodegen tests passed: text QR size=%d, binary QR size=%d\n", size, size2);
    return 0;
}
