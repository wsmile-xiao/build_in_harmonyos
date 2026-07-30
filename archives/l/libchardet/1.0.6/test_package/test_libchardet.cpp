#include <chardet.h>

#include <cstdio>
#include <cstring>

static int check_detect(const char *label, const char *data, size_t size, const char *encoding, short bom) {
    DetectObj *obj = detect_obj_init();
    if (obj == nullptr) {
        std::printf("%s: detect_obj_init failed\n", label);
        return 1;
    }

    short rc = detect_r(data, size, &obj);
    if (rc != CHARDET_SUCCESS) {
        std::printf("%s: detect_r returned %d\n", label, rc);
        detect_obj_free(&obj);
        return 1;
    }

    int failed = 0;
    if (obj->encoding == nullptr || std::strcmp(obj->encoding, encoding) != 0) {
        std::printf("%s: expected encoding %s, got %s\n", label, encoding, obj->encoding ? obj->encoding : "<null>");
        failed = 1;
    }
    if (obj->bom != bom) {
        std::printf("%s: expected BOM %d, got %d\n", label, bom, obj->bom);
        failed = 1;
    }
    if (obj->confidence <= 0.0f) {
        std::printf("%s: expected positive confidence, got %f\n", label, obj->confidence);
        failed = 1;
    }

    detect_obj_free(&obj);
    return failed;
}

int main() {
    const char *version = detect_version();
    if (version == nullptr || std::strlen(version) == 0) {
        std::printf("detect_version returned an empty value\n");
        return 1;
    }

#ifndef CHARDET_BINARY_SAFE
    std::printf("CHARDET_BINARY_SAFE is not defined\n");
    return 1;
#endif

#ifndef CHARDET_BOM_CHECK
    std::printf("CHARDET_BOM_CHECK is not defined\n");
    return 1;
#endif

    const char bom_text[] = "\xEF\xBB\xBF" "HarmonyOS charset detector smoke test";
    if (check_detect("utf8-bom", bom_text, sizeof(bom_text) - 1, "UTF-8", 1) != 0) {
        return 1;
    }

    const char ascii_text[] = "HarmonyOS charset detector smoke test";
    if (check_detect("ascii", ascii_text, sizeof(ascii_text) - 1, "ASCII", 0) != 0) {
        return 1;
    }

    std::printf("libchardet %s smoke OK\n", version);
    return 0;
}
