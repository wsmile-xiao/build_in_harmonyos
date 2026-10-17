#include <stdio.h>
#include <stdlib.h>
#include "audaspace/AUD_Sound.h"
#include "audaspace/AUD_Types.h"

int main(void) {
    // 1. Create a sine wave sound (440Hz, 48kHz) — core generator API
    AUD_Sound *sine = AUD_Sound_sine(440.0f, AUD_RATE_48000);
    if (!sine) {
        fprintf(stderr, "FAIL: AUD_Sound_sine returned NULL\n");
        return 1;
    }

    // 2. Query specs — verifies ISound -> Specs path is functional
    AUD_Specs specs = AUD_Sound_getSpecs(sine);
    printf("sine specs: rate=%.0f channels=%d\n", specs.rate, specs.channels);
    if (specs.rate != AUD_RATE_48000) {
        fprintf(stderr, "FAIL: unexpected rate\n");
        AUD_Sound_free(sine);
        return 1;
    }

    // 3. Query length
    int len = AUD_Sound_getLength(sine);
    printf("sine length: %d\n", len);

    // 4. Create silence sound — second generator API
    AUD_Sound *sil = AUD_Sound_silence(AUD_RATE_48000);
    if (!sil) {
        fprintf(stderr, "FAIL: AUD_Sound_silence returned NULL\n");
        AUD_Sound_free(sine);
        return 1;
    }

    // 5. Apply an effect (volume) — verifies fx/ chain works
    AUD_Sound *vol = AUD_Sound_volume(sine, 0.5f);
    if (!vol) {
        fprintf(stderr, "FAIL: AUD_Sound_volume returned NULL\n");
        AUD_Sound_free(sil);
        AUD_Sound_free(sine);
        return 1;
    }
    printf("volume effect: OK\n");

    // Cleanup — each sound owns its own ref; volume shares sine's data
    AUD_Sound_free(vol);
    AUD_Sound_free(sil);
    AUD_Sound_free(sine);

    printf("test audaspace 1.5.0: OK\n");
    return 0;
}
