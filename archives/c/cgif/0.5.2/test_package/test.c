#include <stdlib.h>
#include <stdint.h>
#include <string.h>

#include "cgif.h"

int main(void) {
    uint8_t palette[] = {0xFF, 0x00, 0x00,
                         0x00, 0xFF, 0x00,
                         0x00, 0x00, 0xFF};
    uint8_t imageData[] = {0, 1, 2, 0, 1, 2, 0, 1, 2};

    CGIF_Config gConfig;
    memset(&gConfig, 0, sizeof(gConfig));
    gConfig.width = 3;
    gConfig.height = 3;
    gConfig.pGlobalPalette = palette;
    gConfig.numGlobalPaletteEntries = 3;
    gConfig.path = "test_output.gif";

    CGIF *pGIF = cgif_newgif(&gConfig);
    if (pGIF == NULL) {
        return 1;
    }

    CGIF_FrameConfig fConfig;
    memset(&fConfig, 0, sizeof(fConfig));
    fConfig.pImageData = imageData;

    if (cgif_addframe(pGIF, &fConfig) != CGIF_OK) {
        cgif_close(pGIF);
        return 1;
    }

    if (cgif_close(pGIF) != CGIF_OK) {
        return 1;
    }

    return 0;
}
