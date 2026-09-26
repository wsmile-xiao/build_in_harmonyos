#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <vector>

#include "tinyexr.h"

static int g_failures = 0;

static void check(int cond, const char *msg)
{
    if (cond) {
        std::printf("ok - %s\n", msg);
    } else {
        std::printf("FAILED - %s\n", msg);
        g_failures++;
    }
}

int main()
{
#if defined(__OHOS__)
    check(1, "__OHOS__ is defined");
#else
    check(0, "__OHOS__ is defined");
#endif

    const int width = 4;
    const int height = 2;
    std::vector<float> rgba(static_cast<size_t>(width * height * 4));
    for (int i = 0; i < width * height; ++i) {
        rgba[static_cast<size_t>(i * 4 + 0)] = 0.1f * static_cast<float>(i);
        rgba[static_cast<size_t>(i * 4 + 1)] = 0.2f;
        rgba[static_cast<size_t>(i * 4 + 2)] = 0.3f;
        rgba[static_cast<size_t>(i * 4 + 3)] = 1.0f;
    }

    const char *err = nullptr;
    int ret = SaveEXR(rgba.data(), width, height, 4, 1, "ohos_roundtrip.exr", &err);
    check(ret == TINYEXR_SUCCESS, "SaveEXR 4x2 RGBA");
    if (ret != TINYEXR_SUCCESS && err) {
        FreeEXRErrorMessage(err);
        err = nullptr;
    }

    check(IsEXR("ohos_roundtrip.exr") == TINYEXR_SUCCESS, "IsEXR accepts saved file");
    check(IsEXR("tinyexr_missing_file.exr") != TINYEXR_SUCCESS, "IsEXR rejects missing file");

    EXRVersion version = {};
    ret = ParseEXRVersionFromFile(&version, "ohos_roundtrip.exr");
    check(ret == TINYEXR_SUCCESS, "ParseEXRVersionFromFile");
    if (ret == TINYEXR_SUCCESS) {
        check(version.multipart == 0, "saved EXR is single-part");
    }

    float *loaded = nullptr;
    int loaded_w = 0;
    int loaded_h = 0;
    ret = LoadEXR(&loaded, &loaded_w, &loaded_h, "ohos_roundtrip.exr", &err);
    check(ret == TINYEXR_SUCCESS, "LoadEXR round-trip");
    if (ret != TINYEXR_SUCCESS && err) {
        FreeEXRErrorMessage(err);
        err = nullptr;
    }
    check(loaded_w == width, "loaded width is 4");
    check(loaded_h == height, "loaded height is 2");
    if (loaded) {
        check(loaded[3] > 0.9f && loaded[3] < 1.1f, "loaded alpha near 1");
        free(loaded);
    } else {
        check(0, "loaded pixels non-null");
    }

    std::remove("ohos_roundtrip.exr");
    if (g_failures == 0) {
        std::printf("HMBS_TEST_PACKAGE_RESULT: PASS\n");
        return 0;
    }
    std::printf("HMBS_TEST_PACKAGE_RESULT: FAIL (%d)\n", g_failures);
    return 1;
}
