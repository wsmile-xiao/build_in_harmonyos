#include <stdio.h>
#include <stdlib.h>
#include <turbojpeg.h>

int main(void)
{
    enum { width = 16, height = 16, channels = 3 };
    unsigned char input[width * height * channels];
    unsigned char output[sizeof(input)] = {0};
    unsigned char *jpeg = NULL;
    unsigned long jpeg_size = 0;
    tjhandle compressor = NULL;
    tjhandle decompressor = NULL;
    int result = 1;

    for (size_t i = 0; i < sizeof(input); i += channels) {
        input[i] = 36;
        input[i + 1] = 124;
        input[i + 2] = 216;
    }
    compressor = tjInitCompress();
    decompressor = tjInitDecompress();
    if (!compressor || !decompressor) goto done;
    if (tjCompress2(compressor, input, width, 0, height, TJPF_RGB,
                    &jpeg, &jpeg_size, TJSAMP_444, 95, 0) != 0) goto done;
    if (!jpeg || jpeg_size < 100) goto done;
    if (tjDecompress2(decompressor, jpeg, jpeg_size, output, width, 0,
                      height, TJPF_RGB, 0) != 0) goto done;
    for (size_t i = 0; i < sizeof(input); ++i) {
        int delta = (int)input[i] - (int)output[i];
        if (delta < -12 || delta > 12) goto done;
    }
    printf("TurboJPEG RGB compress/decompress passed (%lu JPEG bytes)\n", jpeg_size);
    result = 0;
done:
    if (result) fprintf(stderr, "TurboJPEG round trip failed: %s\n", tjGetErrorStr());
    tjFree(jpeg);
    if (compressor) tjDestroy(compressor);
    if (decompressor) tjDestroy(decompressor);
    return result;
}
