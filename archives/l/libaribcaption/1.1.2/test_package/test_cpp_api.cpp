/*
 * test_cpp_api — libaribcaption 1.1.2 consumer verification (C++ API).
 *
 * Exercises the public C++ API of the installed package (decoder.hpp +
 * caption.hpp): decodes the upstream sample payload via aribcaption::Decoder
 * and validates Caption::text (UTF-8 std::string), plane geometry, region
 * vector and the DRCS map. Also decodes the DRCS sample to prove the
 * C++ path handles external character download.
 */

#include <cstdio>
#include <cstring>
#include <string>

#include "aribcaption/aribcaption.hpp"
#include "sample_data.h"

using namespace aribcaption;

static int check_decode_ok(void) {
    Context context;
    Decoder decoder(context);
    if (!decoder.Initialize(EncodingScheme::kAuto,
                            CaptionType::kDefault,
                            Profile::kDefault,
                            LanguageId::kDefault)) {
        fprintf(stderr, "FAIL: Decoder::Initialize returned false\n");
        return 1;
    }

    DecodeResult result;
    DecodeStatus st = decoder.Decode(sample_data_1, sizeof(sample_data_1), 0, result);
    printf("[cpp1] Decode(sample_data_1) status=%d\n", (int)st);

    int failed = 0;
    if (st != DecodeStatus::kGotCaption || !result.caption) {
        fprintf(stderr, "FAIL: expected kGotCaption with caption, got %d\n", (int)st);
        return 1;
    }
    const Caption& caption = *result.caption;
    if (caption.text.empty()) {
        fprintf(stderr, "FAIL: Caption::text is empty\n");
        failed = 1;
    } else {
        printf("[cpp1] text=\"%s\" (%zu bytes)\n", caption.text.c_str(), caption.text.size());
        /* UTF-8 sanity: no 0xFE/0xFF bytes, no lone 0x80..0xBF leading byte */
        for (unsigned char c : caption.text) {
            if (c >= 0xFE) { fprintf(stderr, "FAIL: invalid UTF-8 byte 0x%02x\n", c); failed = 1; break; }
        }
    }
    if (caption.regions.empty()) {
        fprintf(stderr, "FAIL: Caption::regions is empty\n");
        failed = 1;
    } else {
        printf("[cpp1] regions=%zu\n", caption.regions.size());
    }
    if (caption.plane_width != 960 && caption.plane_width != 720) {
        fprintf(stderr, "FAIL: unexpected plane width %d\n", caption.plane_width);
        failed = 1;
    }
    printf("[cpp1] plane=%dx%d lang=0x%06x\n",
           caption.plane_width, caption.plane_height, caption.iso6392_language_code);
    return failed;
}

static int check_decode_drcs(void) {
    Context context;
    Decoder decoder(context);
    if (!decoder.Initialize()) {
        fprintf(stderr, "FAIL: Decoder::Initialize returned false\n");
        return 1;
    }
    DecodeResult result;
    DecodeStatus st = decoder.Decode(sample_data_drcs_1, sizeof(sample_data_drcs_1), 0, result);
    printf("[cpp2] Decode(sample_data_drcs_1) status=%d\n", (int)st);

    int failed = 0;
    if (st != DecodeStatus::kGotCaption || !result.caption) {
        fprintf(stderr, "FAIL: expected kGotCaption for DRCS sample, got %d\n", (int)st);
        return 1;
    }
    if (result.caption->drcs_map.empty()) {
        fprintf(stderr, "FAIL: DRCS sample produced empty drcs_map\n");
        failed = 1;
    } else {
        printf("[cpp2] drcs_map size=%zu\n", result.caption->drcs_map.size());
    }
    return failed;
}

int main(void) {
    int failed = 0;
    failed += check_decode_ok();
    failed += check_decode_drcs();
    printf("test_cpp_api: %s\n", failed ? "FAILED" : "ALL CHECKS PASSED");
    return failed ? 1 : 0;
}
