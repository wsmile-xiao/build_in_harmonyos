#include <pnglite.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

typedef struct {
    unsigned char data[4096];
    size_t size;
    size_t position;
} memory_png_t;

static int checks_run;
static int checks_failed;

#define CHECK(condition, message)                                               \
    do {                                                                        \
        ++checks_run;                                                           \
        if (!(condition)) {                                                     \
            ++checks_failed;                                                    \
            fprintf(stderr, "FAIL: %s (line %d)\n", (message), __LINE__);      \
        }                                                                       \
    } while (0)

static unsigned memory_write(void *input, size_t size, size_t count, void *opaque)
{
    memory_png_t *memory = (memory_png_t *)opaque;
    size_t bytes = size * count;

    if (memory->size + bytes > sizeof(memory->data)) {
        return 0;
    }
    memcpy(memory->data + memory->size, input, bytes);
    memory->size += bytes;
    return (unsigned)count;
}

static unsigned memory_read(void *output, size_t size, size_t count, void *opaque)
{
    memory_png_t *memory = (memory_png_t *)opaque;
    size_t bytes = size * count;

    if (memory->position + bytes > memory->size) {
        return 0;
    }
    if (output != NULL) {
        memcpy(output, memory->data + memory->position, bytes);
    }
    memory->position += bytes;
    return (unsigned)count;
}

int main(void)
{
    static const unsigned char signature[8] = {
        0x89, 0x50, 0x4e, 0x47, 0x0d, 0x0a, 0x1a, 0x0a
    };
    static const unsigned char pixels[24] = {
        255, 0, 0, 255, 0, 255, 0, 255, 0, 0, 255, 255,
        255, 255, 255, 255, 0, 0, 0, 255, 127, 63, 31, 200
    };
    unsigned char decoded[sizeof(pixels)] = {0};
    memory_png_t memory = {{0}, 0, 0};
    memory_png_t invalid = {{0}, 8, 0};
    memory_png_t truncated = {{0}, 7, 0};
    png_t writer = {0};
    png_t reader = {0};
    png_t rejected = {0};

    CHECK(png_init(NULL, NULL) == PNG_NO_ERROR, "png_init accepts default allocators");
    CHECK(png_open_read(&rejected, NULL, NULL) == PNG_WRONG_ARGUMENTS,
          "read mode rejects missing callback and file pointer");
    CHECK(png_open_write(&rejected, NULL, NULL) == PNG_WRONG_ARGUMENTS,
          "write mode rejects missing callback and file pointer");
    CHECK(strcmp(png_error_string(PNG_NO_ERROR), "No error") == 0,
          "known error code has a stable description");
    CHECK(strcmp(png_error_string(12345), "Unknown error.") == 0,
          "unknown error code has a fallback description");

    CHECK(png_open_write(&writer, memory_write, &memory) == PNG_NO_ERROR,
          "callback writer opens");
    CHECK(png_set_data(&writer, 3, 2, 8, PNG_TRUECOLOR_ALPHA,
                       (unsigned char *)pixels) == PNG_NO_ERROR,
          "RGBA image encodes");
    CHECK(memory.size > 33, "encoded PNG contains IHDR, IDAT and IEND data");
    CHECK(memcmp(memory.data, signature, sizeof(signature)) == 0,
          "encoded image starts with the PNG signature");

    CHECK(png_open_read(&reader, memory_read, &memory) == PNG_NO_ERROR,
          "encoded PNG reopens through callback IO");
    CHECK(reader.width == 3, "decoded width matches");
    CHECK(reader.height == 2, "decoded height matches");
    CHECK(reader.depth == 8, "decoded bit depth matches");
    CHECK(reader.color_type == PNG_TRUECOLOR_ALPHA, "decoded color type matches");
    CHECK(reader.bpp == 4, "decoded bytes per pixel match RGBA");
    CHECK(png_get_data(&reader, decoded) == PNG_NO_ERROR, "pixel data decodes");
    CHECK(memcmp(decoded, pixels, sizeof(pixels)) == 0,
          "decoded pixels equal the source pixels");
    CHECK(strcmp(png_error_string(PNG_DONE), "PNG done") == 0,
          "completion status has a description");

    memset(invalid.data, 0xa5, invalid.size);
    CHECK(png_open_read(&rejected, memory_read, &invalid) == PNG_HEADER_ERROR,
          "invalid signature is rejected");
    CHECK(png_open_read(&rejected, memory_read, &truncated) == PNG_EOF_ERROR,
          "truncated signature reports end of file");

    if (checks_failed != 0) {
        fprintf(stderr, "%d of %d pnglite checks failed\n", checks_failed, checks_run);
        return EXIT_FAILURE;
    }
    printf("pnglite API round-trip: %d assertions passed\n", checks_run);
    return EXIT_SUCCESS;
}
