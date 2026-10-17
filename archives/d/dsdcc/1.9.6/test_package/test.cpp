// test_package consumer test for dsdcc 1.9.6
// Uses only the public installed headers and public API of libdsdcc:
//   - include/dsdcc/dsd_decoder.h  (installed public header)
//   - DSDDecoder public API: constructor, run(short), getters, formatStatusText
#include <cstdio>
#include <cstring>
#include <cstdlib>

#include <dsdcc/dsd_decoder.h>

using namespace DSDcc;

int main(void)
{
    // Public API: construct a decoder with default options
    DSDDecoder decoder;

    // Public API: default decode mode / rate getters
    if (decoder.getSamplesPerSymbol() <= 0) {
        std::fprintf(stderr, "FAIL: getSamplesPerSymbol() should be > 0\n");
        return 1;
    }

    // Public API: feed a stream of zero samples (silence) through the decoder
    // and verify the FSM stays in a stable (non-crashing) state with
    // observable status output produced through the public API.
    for (int i = 0; i < 48000; ++i) {
        decoder.run(0);
    }

    // Public API: symbol sync quality must remain a valid 0..100-ish value
    // after processing silence (no sync found => low quality, but valid)
    int quality = decoder.getSymbolSyncQuality();
    if (quality < 0 || quality > 100) {
        std::fprintf(stderr, "FAIL: getSymbolSyncQuality() out of range: %d\n", quality);
        return 1;
    }

    // Public API: formatStatusText must fill the buffer with status text
    char statusText[256];
    decoder.formatStatusText(statusText);
    if (std::strlen(statusText) == 0) {
        std::fprintf(stderr, "FAIL: formatStatusText() produced empty status\n");
        return 1;
    }

    std::printf("test dsdcc 1.9.6 consumer: OK (sps=%d quality=%d status=%s)\n",
                decoder.getSamplesPerSymbol(), quality, statusText);
    return 0;
}
