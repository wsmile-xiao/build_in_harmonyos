#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <IL/il.h>
#include <IL/ilu.h>

#define W 32
#define H 24

static unsigned char pixels[W * H * 4];
static int failures = 0;

static void check(int cond, const char *msg)
{
    if (cond) {
        printf("ok - %s\n", msg);
    } else {
        fprintf(stderr, "FAIL - %s (ilGetError=0x%x)\n", msg, (unsigned)ilGetError());
        failures++;
    }
}

static void fill_pattern(void)
{
    size_t i;
    for (i = 0; i < (size_t)(W * H * 4); i++) {
        pixels[i] = (unsigned char)((i * 7 + 13) & 0xFF);
    }
}

/* Compare loaded RGBA data against the pattern, accepting a vertical flip
   (DevIL's default origin handling may flip rows across save/load). */
static int data_matches(const unsigned char *data, int flipped)
{
    int x, y;
    for (y = 0; y < H; y++) {
        const unsigned char *row = data + (size_t)y * W * 4;
        const unsigned char *want = pixels + (size_t)(flipped ? (H - 1 - y) : y) * W * 4;
        for (x = 0; x < W * 4; x++) {
            if (row[x] != want[x]) {
                return 0;
            }
        }
    }
    return 1;
}

static void test_lossless_roundtrip(ILenum type, const char *path)
{
    ILuint img;

    ilGenImages(1, &img);
    ilBindImage(img);
    if (!ilTexImage(W, H, 1, 4, IL_RGBA, IL_UNSIGNED_BYTE, pixels)) {
        check(0, "ilTexImage");
        ilDeleteImages(1, &img);
        return;
    }
    ilEnable(IL_FILE_OVERWRITE);
    if (!ilSave(type, path)) {
        check(0, "ilSave");
        ilDeleteImages(1, &img);
        return;
    }
    ilDeleteImages(1, &img);

    ilGenImages(1, &img);
    ilBindImage(img);
    if (!ilLoad(type, path)) {
        check(0, "ilLoad");
        ilDeleteImages(1, &img);
        return;
    }
    check(ilGetInteger(IL_IMAGE_WIDTH) == W && ilGetInteger(IL_IMAGE_HEIGHT) == H,
          "dimensions preserved");
    ilConvertImage(IL_RGBA, IL_UNSIGNED_BYTE);
    {
        const unsigned char *data = (const unsigned char *)ilGetData();
        check(data != NULL && (data_matches(data, 0) || data_matches(data, 1)),
              "pixels preserved");
    }
    ilDeleteImages(1, &img);
    remove(path);
}

static void test_jpeg_roundtrip(void)
{
    ILuint img;

    ilGenImages(1, &img);
    ilBindImage(img);
    if (!ilTexImage(W, H, 1, 4, IL_RGBA, IL_UNSIGNED_BYTE, pixels)) {
        check(0, "ilTexImage (jpeg)");
        ilDeleteImages(1, &img);
        return;
    }
    ilEnable(IL_FILE_OVERWRITE);
    if (!ilSave(IL_JPG, "devil_test.jpg")) {
        check(0, "ilSave(IL_JPG)");
        ilDeleteImages(1, &img);
        return;
    }
    ilDeleteImages(1, &img);

    ilGenImages(1, &img);
    ilBindImage(img);
    if (!ilLoad(IL_JPG, "devil_test.jpg")) {
        check(0, "ilLoad(IL_JPG)");
        ilDeleteImages(1, &img);
        return;
    }
    check(ilGetInteger(IL_IMAGE_WIDTH) == W && ilGetInteger(IL_IMAGE_HEIGHT) == H,
          "jpeg dimensions preserved");
    {
        const unsigned char *data = (const unsigned char *)ilGetData();
        size_t i, nonzero = 0;
        for (i = 0; data != NULL && i < (size_t)(W * H * 4); i++) {
            nonzero += (data[i] != 0);
        }
        check(nonzero > 0, "jpeg decodes to non-empty pixels");
    }
    ilDeleteImages(1, &img);
    remove("devil_test.jpg");
}

int main(void)
{
    if (ilGetInteger(IL_VERSION_NUM) < IL_VERSION ||
        ilGetInteger(ILU_VERSION_NUM) < ILU_VERSION) {
        fprintf(stderr, "FAIL - devil/ilu version mismatch\n");
        return 1;
    }
    printf("ok - devil runtime version IL=%u ILU=%u\n",
           (unsigned)ilGetInteger(IL_VERSION_NUM),
           (unsigned)ilGetInteger(ILU_VERSION_NUM));

    ilInit();
    fill_pattern();
    test_lossless_roundtrip(IL_PNG, "devil_test.png");
    test_jpeg_roundtrip();
    ilShutDown();

    if (failures) {
        fprintf(stderr, "test devil 1.8.0.40.g6f3d5e9b: FAIL (%d checks failed)\n", failures);
        return 1;
    }
    printf("test devil 1.8.0.40.g6f3d5e9b: OK\n");
    return 0;
}
