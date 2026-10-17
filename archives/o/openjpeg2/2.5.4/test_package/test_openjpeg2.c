#include <stdio.h>
#include <string.h>

#include <openjpeg.h>

static int check(int condition, const char *message)
{
    if (!condition) {
        fprintf(stderr, "FAIL: %s\n", message);
        return 1;
    }
    return 0;
}

static OPJ_BOOL encode_image(const char *path, const OPJ_INT32 pixels[4])
{
    opj_cparameters_t parameters;
    opj_image_cmptparm_t component;
    opj_image_t *image = NULL;
    opj_codec_t *codec = NULL;
    opj_stream_t *stream = NULL;
    OPJ_BOOL result = OPJ_FALSE;

    opj_set_default_encoder_parameters(&parameters);
    parameters.tcp_numlayers = 1;
    parameters.cp_disto_alloc = 1;
    parameters.tcp_rates[0] = 0;
    parameters.irreversible = 0;
    parameters.numresolution = 1;

    memset(&component, 0, sizeof(component));
    component.dx = 1;
    component.dy = 1;
    component.w = 2;
    component.h = 2;
    component.prec = 8;
    component.sgnd = 0;

    image = opj_image_create(1, &component, OPJ_CLRSPC_GRAY);
    if (image == NULL) {
        goto cleanup;
    }
    image->x0 = 0;
    image->y0 = 0;
    image->x1 = 2;
    image->y1 = 2;
    memcpy(image->comps[0].data, pixels, 4 * sizeof(pixels[0]));

    codec = opj_create_compress(OPJ_CODEC_J2K);
    if (codec == NULL || !opj_setup_encoder(codec, &parameters, image)) {
        goto cleanup;
    }

    stream = opj_stream_create_default_file_stream(path, OPJ_FALSE);
    if (stream == NULL) {
        goto cleanup;
    }

    result = opj_start_compress(codec, image, stream) &&
             opj_encode(codec, stream) &&
             opj_end_compress(codec, stream);

cleanup:
    opj_stream_destroy(stream);
    opj_destroy_codec(codec);
    opj_image_destroy(image);
    return result;
}

static OPJ_BOOL decode_image(
    const char *path,
    OPJ_INT32 pixels[4],
    OPJ_UINT32 *width,
    OPJ_UINT32 *height)
{
    opj_dparameters_t parameters;
    opj_image_t *image = NULL;
    opj_codec_t *codec = NULL;
    opj_stream_t *stream = NULL;
    OPJ_BOOL result = OPJ_FALSE;

    opj_set_default_decoder_parameters(&parameters);
    codec = opj_create_decompress(OPJ_CODEC_J2K);
    if (codec == NULL || !opj_setup_decoder(codec, &parameters)) {
        goto cleanup;
    }

    stream = opj_stream_create_default_file_stream(path, OPJ_TRUE);
    if (stream == NULL || !opj_read_header(stream, codec, &image) ||
        !opj_decode(codec, stream, image) ||
        !opj_end_decompress(codec, stream)) {
        goto cleanup;
    }

    if (image == NULL || image->numcomps != 1 || image->comps[0].data == NULL ||
        image->comps[0].w != 2 || image->comps[0].h != 2) {
        goto cleanup;
    }

    *width = image->comps[0].w;
    *height = image->comps[0].h;
    memcpy(pixels, image->comps[0].data, 4 * sizeof(pixels[0]));
    result = OPJ_TRUE;

cleanup:
    opj_stream_destroy(stream);
    opj_destroy_codec(codec);
    opj_image_destroy(image);
    return result;
}

int main(void)
{
    static const char encoded_path[] = "openjpeg2-smoke.j2k";
    const OPJ_INT32 input[4] = {0, 32, 127, 255};
    OPJ_INT32 output[4] = {0, 0, 0, 0};
    OPJ_UINT32 width = 0;
    OPJ_UINT32 height = 0;
    opj_cparameters_t defaults;
    const char *version = opj_version();
    OPJ_BOOL encoded;
    OPJ_BOOL decoded;
    int failures = 0;

    failures += check(
        version != NULL && strcmp(version, "2.5.4") == 0,
        "opj_version reports 2.5.4");

    opj_set_default_encoder_parameters(&defaults);
    failures += check(
        defaults.numresolution > 0 &&
            defaults.cblockw_init > 0 &&
            defaults.cblockh_init > 0,
        "default encoder parameters initialize coding geometry");

    encoded = encode_image(encoded_path, input);
    failures += check(encoded, "lossless J2K encoding succeeds");

    decoded = encoded && decode_image(encoded_path, output, &width, &height);
    failures += check(decoded, "J2K decoding succeeds");
    failures += check(width == 2 && height == 2, "decoded geometry is 2x2");
    failures += check(
        memcmp(input, output, sizeof(input)) == 0,
        "decoded samples match the input");

    remove(encoded_path);

    if (failures != 0) {
        return 1;
    }

    printf("openjpeg2 consumer checks passed (6/6)\n");
    return 0;
}
