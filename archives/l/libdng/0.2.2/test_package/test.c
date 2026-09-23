#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

#include "libdng.h"

static const char *writable_tmpdir(void) {
    const char *vars[] = {"TMPDIR", "TMP", "TEMP", NULL};
    for (int i = 0; vars[i]; i++) {
        const char *v = getenv(vars[i]);
        if (v && v[0] != 0) {
            return v;
        }
    }
    return ".";
}

static void output_path(const char *name, char *out, size_t cap) {
    const char *dir = writable_tmpdir();
    if (!dir || dir[0] == 0 || (dir[0] == '.' && dir[1] == 0)) {
        snprintf(out, cap, "%s", name);
    } else {
        snprintf(out, cap, "%s/%s", dir, name);
    }
}

static int check_init_new_free(void) {
    libdng_info info;
    memset(&info, 0, sizeof(info));
    /* Upstream libdng_init() always returns 0 on success (src/libdng.c);
       it only registers the TIFF tag extender. Do not treat 0 as failure. */
    libdng_init();
    libdng_new(&info);
    libdng_free(&info);
    printf("CHECK-OK: init_new_free\n");
    return 1;
}

static int check_mode_rggb(void) {
    libdng_info info;
    memset(&info, 0, sizeof(info));
    libdng_new(&info);
    if (!libdng_set_mode_from_name(&info, "RGGB")) {
        libdng_free(&info);
        return 0;
    }
    if (info.bit_depth != 8) {
        fprintf(stderr, "unexpected bit_depth %u\n", (unsigned)info.bit_depth);
        libdng_free(&info);
        return 0;
    }
    if (info.cfapattern[0] != 0 || info.cfapattern[1] != 1 ||
        info.cfapattern[2] != 1 || info.cfapattern[3] != 2) {
        fprintf(stderr, "unexpected cfapattern\n");
        libdng_free(&info);
        return 0;
    }
    libdng_free(&info);
    printf("CHECK-OK: mode_rggb_bitdepth8\n");
    return 1;
}

static int check_metadata_setters(void) {
    libdng_info info;
    memset(&info, 0, sizeof(info));
    libdng_new(&info);
    int ok = 1;
    ok &= (libdng_set_make_model(&info, "HMBS", "TestCam") == 1);
    ok &= (libdng_set_software(&info, "hmbs-smoke") == 1);
    ok &= (libdng_set_orientation(&info, 1) == 1);
    ok &= (libdng_set_exposure_time(&info, 0.01f) == 1);
    ok &= (libdng_set_fnumber(&info, 2.8f) == 1);
    ok &= (libdng_set_iso(&info, 100) == 1);
    ok &= (libdng_set_neutral(&info, 1.0f, 1.0f, 1.0f) == 1);
    if (!ok) {
        libdng_free(&info);
        return 0;
    }
    if (strcmp(info.camera_make, "HMBS") != 0 || strcmp(info.camera_model, "TestCam") != 0) {
        libdng_free(&info);
        return 0;
    }
    libdng_free(&info);
    printf("CHECK-OK: metadata_setters\n");
    return 1;
}

static int check_write_minimal_dng(void) {
    const unsigned width = 16;
    const unsigned height = 16;
    const size_t len = (size_t)width * (size_t)height;
    uint8_t *data = (uint8_t *)calloc(1, len);
    if (!data) {
        return 0;
    }
    for (size_t i = 0; i < len; i++) {
        data[i] = (uint8_t)(i & 0xff);
    }
    libdng_info info;
    memset(&info, 0, sizeof(info));
    libdng_new(&info);
    int ok = 1;
    ok &= (libdng_set_mode_from_name(&info, "RGGB") == 1);
    ok &= (libdng_set_make_model(&info, "HMBS", "TestCam") == 1);
    ok &= (libdng_set_software(&info, "hmbs-smoke") == 1);
    if (!ok) {
        free(data);
        libdng_free(&info);
        return 0;
    }
    char outbuf[1024];
    output_path("libdng_smoke.dng", outbuf, sizeof(outbuf));
    const char *path = outbuf;
    if (!libdng_write(&info, path, width, height, data, len)) {
        fprintf(stderr, "libdng_write failed\n");
        free(data);
        libdng_free(&info);
        return 0;
    }
    free(data);
    libdng_free(&info);
    struct stat st;
    if (stat(path, &st) != 0 || st.st_size <= 0) {
        fprintf(stderr, "output dng missing or empty\n");
        return 0;
    }
    printf("CHECK-OK: write_minimal_dng size=%lld\n", (long long)st.st_size);
    return 1;
}

int main(void) {
    int passed = 0;
    passed += check_init_new_free();
    passed += check_mode_rggb();
    passed += check_metadata_setters();
    passed += check_write_minimal_dng();
    if (passed == 4) {
        printf("libdng smoke: all 4 checks passed\n");
        return 0;
    }
    fprintf(stderr, "libdng smoke: %d/4 checks passed\n", passed);
    return 1;
}
