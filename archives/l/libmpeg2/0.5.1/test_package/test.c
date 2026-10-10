/* Installed-package consumer: MPEG2 file -> RGB frames -> PPM file roundtrip.
 * The fixture is a complete 12-frame upstream stream, not fabricated data.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <mpeg2dec/mpeg2.h>
#include <mpeg2dec/mpeg2convert.h>
#include "mpeg2_fixture.h"

#ifdef _WIN32
#include <direct.h>
#include <process.h>
#define make_dir(path) _mkdir(path)
#define remove_dir(path) _rmdir(path)
#define process_id() _getpid()
#else
#include <sys/stat.h>
#include <unistd.h>
#define make_dir(path) mkdir(path, 0700)
#define remove_dir(path) rmdir(path)
#define process_id() getpid()
#endif

static const uint32_t expected_rgb_hashes[12] = {
    UINT32_C(0x25ea4d85), UINT32_C(0x25ea4d85), UINT32_C(0x25ea4d85),
    UINT32_C(0xc8714fdd), UINT32_C(0x0d882ef5), UINT32_C(0xb9ae82cd),
    UINT32_C(0x74fe2b65), UINT32_C(0xcd60b6bd), UINT32_C(0x86267ad5),
    UINT32_C(0x86267ad5), UINT32_C(0x86267ad5), UINT32_C(0x86267ad5)
};

static uint32_t rgb_hash(const unsigned char *data, size_t size) {
    uint32_t hash = UINT32_C(2166136261);
    size_t i;
    for (i = 0; i < size; ++i) {
        hash ^= data[i];
        hash *= UINT32_C(16777619);
    }
    return hash;
}

static int frame_roundtrip(const char *dir, unsigned frame,
                           const mpeg2_info_t *info, uint32_t *hash) {
    char path[128];
    unsigned char pixels[12 * 12 * 3], restored[sizeof(pixels)];
    char header[14];
    const char expected_header[] = "P6\n12 12\n255\n";
    FILE *file;
    unsigned y;
    int failed = 0;
    if (!info->display_fbuf || !info->display_fbuf->buf[0] ||
        info->sequence->picture_width != 12 ||
        info->sequence->picture_height != 12 ||
        info->sequence->width != 16 || frame >= 12) {
        fputs("unexpected decoded frame layout\n", stderr);
        return 1;
    }
    /* The RGB converter's stride is the aligned sequence width, not 12. */
    for (y = 0; y < 12; ++y)
        memcpy(pixels + y * 36,
               info->display_fbuf->buf[0] + y * info->sequence->width * 3, 36);
    *hash = rgb_hash(pixels, sizeof(pixels));
    snprintf(path, sizeof(path), "%s/frame-%02u.ppm", dir, frame);
    file = fopen(path, "wb");
    if (!file)
        return 1;
    if (fwrite(expected_header, 1, sizeof(expected_header) - 1, file) !=
        sizeof(expected_header) - 1 ||
        fwrite(pixels, 1, sizeof(pixels), file) != sizeof(pixels))
        failed = 1;
    if (fclose(file) != 0)
        failed = 1;
    file = fopen(path, "rb");
    if (!file) {
        remove(path);
        return 1;
    }
    if (fread(header, 1, sizeof(expected_header) - 1, file) !=
        sizeof(expected_header) - 1 ||
        memcmp(header, expected_header, sizeof(expected_header) - 1) != 0 ||
        fread(restored, 1, sizeof(restored), file) != sizeof(restored) ||
        memcmp(restored, pixels, sizeof(pixels)) != 0 ||
        fgetc(file) != EOF || ferror(file))
        failed = 1;
    if (fclose(file) != 0)
        failed = 1;
    if (remove(path) != 0)
        failed = 1;
    return failed;
}

int main(void) {
    char dir[80], input_path[128];
    unsigned char buffer[7];
    mpeg2dec_t *decoder = NULL;
    const mpeg2_info_t *info;
    FILE *input = NULL;
    unsigned frames = 0, sequence_count = 0;
    int failed = 0, input_created = 0;
    size_t size;
    if (MPEG2_RELEASE != MPEG2_VERSION(0, 5, 1))
        return 1;
    /* Use Conan's task-private working directory: OHOS /tmp is not writable. */
    snprintf(dir, sizeof(dir), "libmpeg2-e2e-%lu", (unsigned long)process_id());
    if (make_dir(dir) != 0) {
        perror("create consumer directory");
        return 1;
    }
    snprintf(input_path, sizeof(input_path), "%s/input.m2v", dir);
    input = fopen(input_path, "wb");
    if (!input) {
        failed = 1;
        goto cleanup;
    }
    input_created = 1;
    failed = fwrite(mpeg2_fixture, 1, sizeof(mpeg2_fixture), input) != sizeof(mpeg2_fixture);
    if (fclose(input) != 0)
        failed = 1;
    input = NULL;
    if (failed)
        goto cleanup;
    input = fopen(input_path, "rb");
    /* Portable reference IDCT keeps golden pixels independent of CPU SIMD. */
    mpeg2_accel(0);
    decoder = mpeg2_init();
    if (!input || !decoder) {
        failed = 1;
        goto cleanup;
    }
    info = mpeg2_info(decoder);
    if (!info) {
        failed = 1;
        goto cleanup;
    }
    /* Tiny reads exercise start-code boundaries and actual streaming input. */
    for (;;) {
        mpeg2_state_t state = mpeg2_parse(decoder);
        if (state == STATE_BUFFER) {
            size = fread(buffer, 1, sizeof(buffer), input);
            if (!size) {
                if (ferror(input))
                    failed = 1;
                break;
            }
            mpeg2_buffer(decoder, buffer, buffer + size);
        } else if (state == STATE_SEQUENCE) {
            ++sequence_count;
            if (mpeg2_convert(decoder, mpeg2convert_rgb24, NULL) != 0) {
                failed = 1;
                break;
            }
        } else if (state == STATE_SLICE || state == STATE_END || state == STATE_INVALID_END) {
            if (info->display_fbuf) {
                uint32_t hash;
                if (frame_roundtrip(dir, frames, info, &hash)) {
                    failed = 1;
                    break;
                }
                printf("FRAME %u RGB_FNV1A=%08lx\n", frames, (unsigned long)hash);
                if (hash != expected_rgb_hashes[frames])
                    failed = 1;
                ++frames;
            }
        } else if (state == STATE_INVALID) {
            fputs("invalid MPEG input\n", stderr);
            failed = 1;
            break;
        }
    }
    if (frames != 12 || sequence_count != 1) {
        fprintf(stderr, "unexpected sequence/frame count: %u/%u\n", sequence_count, frames);
        failed = 1;
    }
cleanup:
    if (decoder)
        mpeg2_close(decoder);
    if (input && fclose(input) != 0)
        failed = 1;
    if (input_created && remove(input_path) != 0)
        failed = 1;
    if (remove_dir(dir) != 0)
        failed = 1;
    if (failed) {
        fputs("libmpeg2 complete consumer FAIL\n", stderr);
        return 1;
    }
    puts("LIBMPEG2_HARMONY_E2E_PASS frames=12 picture=12x12 RGB24=verified PPM=roundtrip");
    puts("libmpeg2 consumer PASS");
    return 0;
}
