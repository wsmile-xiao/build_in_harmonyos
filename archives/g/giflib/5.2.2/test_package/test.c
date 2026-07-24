#include <gif_lib.h>

#include <stdio.h>

int main(void) {
    const char *path = "giflib-roundtrip.gif";
    GifColorType colors[2] = {{0, 0, 0}, {255, 255, 255}};
    ColorMapObject *color_map = GifMakeMapObject(2, colors);
    GifPixelType pixel = 1;
    int error = 0;

    if (color_map == NULL) {
        fprintf(stderr, "GifMakeMapObject failed\n");
        return 1;
    }

    GifFileType *writer = EGifOpenFileName(path, false, &error);
    if (writer == NULL) {
        fprintf(stderr, "EGifOpenFileName failed: %d\n", error);
        GifFreeMapObject(color_map);
        remove(path);
        return 1;
    }
    if (EGifPutScreenDesc(writer, 1, 1, 8, 0, color_map) == GIF_ERROR ||
        EGifPutImageDesc(writer, 0, 0, 1, 1, false, NULL) == GIF_ERROR ||
        EGifPutLine(writer, &pixel, 1) == GIF_ERROR) {
        fprintf(stderr, "GIF encoding failed: %d\n", writer->Error);
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

    GifFileType *reader = DGifOpenFileName(path, &error);
    if (reader == NULL) {
        fprintf(stderr, "DGifOpenFileName failed: %d\n", error);
        remove(path);
        return 1;
    }
    if (DGifSlurp(reader) == GIF_ERROR) {
        fprintf(stderr, "GIF decoding failed: %d\n", reader->Error);
        DGifCloseFile(reader, &error);
        remove(path);
        return 1;
    }
    if (reader->SWidth != 1 || reader->SHeight != 1 ||
        reader->ImageCount != 1 ||
        reader->SavedImages[0].RasterBits[0] != pixel) {
        fprintf(stderr, "GIF round-trip content mismatch\n");
        DGifCloseFile(reader, &error);
        remove(path);
        return 1;
    }
    if (DGifCloseFile(reader, &error) == GIF_ERROR) {
        fprintf(stderr, "GIF close failed: %d\n", error);
        remove(path);
        return 1;
    }

    remove(path);
    printf("giflib encode/decode round-trip: PASS\n");
    return 0;
}
