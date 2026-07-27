/*
 * test_openjpeg.c — Consumer test for openjpeg Conan package
 *
 * Exercises the openjpeg API:
 * 1. Calls opj_version() to verify library linkage
 * 2. Creates and destroys a decompressor handle to verify API availability
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <openjpeg.h>

int main(void)
{
    /* Verify library is linked and returns expected version */
    const char *version = opj_version();
    if (version == NULL || strlen(version) == 0) {
        fprintf(stderr, "FAIL: opj_version() returned NULL or empty\n");
        return 1;
    }
    printf("OpenJPEG version: %s\n", version);

    /* Verify the version string starts with expected major version */
    if (strncmp(version, "2.5", 3) != 0) {
        fprintf(stderr, "FAIL: unexpected version: %s (expected 2.5.x)\n", version);
        return 1;
    }

    /* Create and destroy a decompressor to exercise the API */
    opj_dparameters_t parameters;
    opj_set_default_decoder_parameters(&parameters);

    opj_codec_t *decompressor = opj_create_decompress(OPJ_CODEC_J2K);
    if (decompressor == NULL) {
        fprintf(stderr, "FAIL: opj_create_decompress returned NULL\n");
        return 1;
    }
    opj_destroy_codec(decompressor);

    /* Create and destroy a compressor to exercise the encoder API */
    opj_cparameters_t cparameters;
    memset(&cparameters, 0, sizeof(cparameters));
    opj_set_default_encoder_parameters(&cparameters);

    opj_codec_t *compressor = opj_create_compress(OPJ_CODEC_J2K);
    if (compressor == NULL) {
        fprintf(stderr, "FAIL: opj_create_compress returned NULL\n");
        return 1;
    }
    opj_destroy_codec(compressor);

    printf("All tests passed.\n");
    return 0;
}
