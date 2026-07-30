#include <gif_lib.h>

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int make_path(char *buffer, size_t size, const char *name) {
    const char *tmpdir = getenv("TMPDIR");
    int written;

    if (tmpdir == NULL || tmpdir[0] == '\0') {
        fprintf(stderr, "TMPDIR is required\n");
        return 1;
    }
    written = snprintf(buffer, size, "%s/%s", tmpdir, name);
    if (written < 0 || (size_t)written >= size) {
        fprintf(stderr, "temporary path is too long\n");
        return 1;
    }
    return 0;
}

static int test_roundtrip(void) {
    char path[1024];
    GifColorType colors[2] = {{0, 0, 0}, {255, 255, 255}};
    ColorMapObject *color_map;
    GifPixelType pixel = 1;
    GifFileType *writer;
    GifFileType *reader;
    int error = 0;

    if (make_path(path, sizeof(path), "giflib-roundtrip.gif") != 0) {
        return 1;
    }
    remove(path);
    color_map = GifMakeMapObject(2, colors);
    if (color_map == NULL) {
        fprintf(stderr, "GifMakeMapObject failed\n");
        return 1;
    }

    writer = EGifOpenFileName(path, false, &error);
    if (writer == NULL) {
        fprintf(stderr, "EGifOpenFileName failed: %d\n", error);
        GifFreeMapObject(color_map);
        return 1;
    }
    if (EGifPutScreenDesc(writer, 1, 1, 8, 0, color_map) == GIF_ERROR ||
        EGifPutImageDesc(writer, 0, 0, 1, 1, false, NULL) == GIF_ERROR ||
        EGifPutLine(writer, &pixel, 1) == GIF_ERROR) {
        int operation_error = writer->Error;
        fprintf(stderr, "GIF encoding failed: %d\n", operation_error);
        EGifCloseFile(writer, &error);
        GifFreeMapObject(color_map);
        remove(path);
        return 1;
    }
    if (EGifCloseFile(writer, &error) == GIF_ERROR) {
        fprintf(stderr, "EGifCloseFile failed: %d\n", error);
        GifFreeMapObject(color_map);
        remove(path);
        return 1;
    }
    GifFreeMapObject(color_map);

    reader = DGifOpenFileName(path, &error);
    if (reader == NULL) {
        fprintf(stderr, "DGifOpenFileName failed: %d\n", error);
        remove(path);
        return 1;
    }
    if (DGifSlurp(reader) == GIF_ERROR) {
        int operation_error = reader->Error;
        fprintf(stderr, "GIF decoding failed: %d\n", operation_error);
        DGifCloseFile(reader, &error);
        remove(path);
        return 1;
    }
    if (reader->SWidth != 1 || reader->SHeight != 1 ||
        reader->ImageCount != 1 || reader->SavedImages == NULL ||
        reader->SavedImages[0].RasterBits == NULL ||
        reader->SavedImages[0].RasterBits[0] != pixel) {
        fprintf(stderr, "GIF round-trip content mismatch\n");
        DGifCloseFile(reader, &error);
        remove(path);
        return 1;
    }
    if (DGifCloseFile(reader, &error) == GIF_ERROR) {
        fprintf(stderr, "DGifCloseFile failed: %d\n", error);
        remove(path);
        return 1;
    }
    if (remove(path) != 0) {
        fprintf(stderr, "failed to remove round-trip file\n");
        return 1;
    }
    puts("giflib round-trip workflow: PASS");
    return 0;
}

static int test_encode_error(void) {
    char path[1024];
    GifColorType colors[2] = {{0, 0, 0}, {255, 255, 255}};
    ColorMapObject *color_map;
    GifFileType *writer;
    int open_error = 0;
    int close_error = 0;
    int second_result;
    int operation_error;

    if (make_path(path, sizeof(path), "giflib-encode-error.gif") != 0) {
        return 1;
    }
    remove(path);
    color_map = GifMakeMapObject(2, colors);
    if (color_map == NULL) {
        fprintf(stderr, "GifMakeMapObject failed\n");
        return 1;
    }
    writer = EGifOpenFileName(path, false, &open_error);
    if (writer == NULL) {
        fprintf(stderr, "EGifOpenFileName failed: %d\n", open_error);
        GifFreeMapObject(color_map);
        return 1;
    }
    if (EGifPutScreenDesc(writer, 1, 1, 8, 0, color_map) == GIF_ERROR) {
        operation_error = writer->Error;
        fprintf(stderr, "initial screen descriptor failed: %d\n", operation_error);
        EGifCloseFile(writer, &close_error);
        GifFreeMapObject(color_map);
        remove(path);
        return 1;
    }
    second_result = EGifPutScreenDesc(writer, 1, 1, 8, 0, color_map);
    operation_error = writer->Error;
    EGifCloseFile(writer, &close_error);
    GifFreeMapObject(color_map);
    remove(path);

    if (second_result != GIF_ERROR || operation_error == 0 || open_error != 0) {
        fprintf(
            stderr,
            "encoding error ownership mismatch: result=%d operation=%d open=%d\n",
            second_result,
            operation_error,
            open_error
        );
        return 1;
    }
    puts("giflib encoder error workflow: PASS");
    return 0;
}

static int test_decode_truncated(void) {
    static const unsigned char truncated_gif[] = {
        'G', 'I', 'F', '8', '9', 'a',
        1, 0, 1, 0, 0x80, 0, 0,
        0, 0, 0, 255, 255, 255,
        0x2c, 0, 0, 0, 0, 1, 0, 1, 0, 0
    };
    char path[1024];
    FILE *stream;
    GifFileType *reader;
    size_t bytes_written;
    int close_result;
    int open_error = 0;
    int close_error = 0;
    int slurp_result;
    int operation_error;

    if (make_path(path, sizeof(path), "giflib-truncated.gif") != 0) {
        return 1;
    }
    remove(path);
    stream = fopen(path, "wb");
    if (stream == NULL) {
        fprintf(stderr, "failed to create truncated fixture\n");
        return 1;
    }
    bytes_written = fwrite(truncated_gif, 1, sizeof(truncated_gif), stream);
    close_result = fclose(stream);
    if (bytes_written != sizeof(truncated_gif) || close_result != 0) {
        fprintf(stderr, "failed to write truncated fixture\n");
        remove(path);
        return 1;
    }

    reader = DGifOpenFileName(path, &open_error);
    if (reader == NULL) {
        fprintf(stderr, "DGifOpenFileName failed: %d\n", open_error);
        remove(path);
        return 1;
    }
    slurp_result = DGifSlurp(reader);
    operation_error = reader->Error;
    DGifCloseFile(reader, &close_error);
    remove(path);

    if (slurp_result != GIF_ERROR || operation_error == 0 || open_error != 0) {
        fprintf(
            stderr,
            "decoding error ownership mismatch: result=%d operation=%d open=%d\n",
            slurp_result,
            operation_error,
            open_error
        );
        return 1;
    }
    puts("giflib truncated decoder workflow: PASS");
    return 0;
}

int main(int argc, char **argv) {
    if (argc != 2) {
        fprintf(stderr, "usage: %s CASE\n", argv[0]);
        return 2;
    }
    if (strcmp(argv[1], "roundtrip") == 0) {
        return test_roundtrip();
    }
    if (strcmp(argv[1], "encode-error") == 0) {
        return test_encode_error();
    }
    if (strcmp(argv[1], "decode-truncated") == 0) {
        return test_decode_truncated();
    }
    fprintf(stderr, "unknown case: %s\n", argv[1]);
    return 2;
}
