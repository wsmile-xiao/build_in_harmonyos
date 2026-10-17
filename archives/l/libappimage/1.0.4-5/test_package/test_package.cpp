// libappimage test package: exercises the public C API against the conan
// package (libappimage.so + generated headers) at runtime.

#include <cstdio>
#include <cstdlib>
#include <cstring>

#include <appimage/appimage.h>

static int failures = 0;

#define CHECK(cond)                                                      \
    do {                                                                 \
        if (!(cond)) {                                                   \
            printf("FAIL: %s (line %d)\n", #cond, __LINE__);            \
            failures++;                                                  \
        }                                                                \
    } while (0)

static void write_file(const char* path, const void* data, size_t size) {
    FILE* f = fopen(path, "wb");
    if (!f) {
        printf("FAIL: cannot create %s\n", path);
        failures++;
        return;
    }
    fwrite(data, 1, size, f);
    fclose(f);
}

int main() {
    const char* regular = "regular.bin";
    const char* type2 = "type2.appimage";

    // 1. a regular (non-AppImage) file
    write_file(regular, "hello world, definitely not an AppImage", 38);
    CHECK(appimage_get_type(regular, false) == -1);  // AppImageFormat::INVALID
    CHECK(appimage_get_payload_offset(regular) == 0);

    char* md5 = appimage_get_md5(regular);
    CHECK(md5 != nullptr);
    if (md5) {
        CHECK(strlen(md5) == 32);
        for (int i = 0; i < 32; i++) {
            char c = md5[i];
            CHECK((c >= '0' && c <= '9') || (c >= 'a' && c <= 'f'));
        }
        free(md5);
    }

    // 2. a crafted Type-2 AppImage header: ELF magic at offset 0 and the
    //    AI\x02 magic bytes at offset 8 (enough for the format detection)
    unsigned char header[16] = {
        0x7f, 0x45, 0x4c, 0x46, 0x02, 0x01, 0x01, 0x00,
        0x41, 0x49, 0x02, 0x00,
        0x00, 0x00, 0x00, 0x00,
    };
    write_file(type2, header, sizeof(header));
    CHECK(appimage_get_type(type2, false) == 2);  // AppImageFormat::TYPE_2

    if (failures != 0) {
        printf("libappimage test_package: %d check(s) FAILED\n", failures);
        return 1;
    }
    printf("libappimage test_package: all checks passed\n");
    return 0;
}
