#include <opus/opus.h>

#include <stdio.h>
#include <string.h>

int main(void)
{
    enum { sample_rate = 48000, frame_size = 960, channels = 1 };
    opus_int16 input[frame_size] = {0};
    opus_int16 output[frame_size] = {0};
    unsigned char packet[4000];
    int error = OPUS_OK;
    int result = 0;
    int bytes;
    int samples;
    OpusEncoder *encoder = NULL;
    OpusDecoder *decoder = NULL;

    encoder = opus_encoder_create(
        sample_rate, channels, OPUS_APPLICATION_AUDIO, &error);
    if (!encoder || error != OPUS_OK) {
        result = 1;
        goto cleanup;
    }
    decoder = opus_decoder_create(sample_rate, channels, &error);
    if (!decoder || error != OPUS_OK) {
        result = 2;
        goto cleanup;
    }
    bytes = opus_encode(
        encoder, input, frame_size, packet, (opus_int32)sizeof(packet));
    if (bytes <= 0) {
        result = 3;
        goto cleanup;
    }
    samples = opus_decode(decoder, packet, bytes, output, frame_size, 0);
    if (samples != frame_size || memcmp(input, output, sizeof(input)) != 0) {
        result = 4;
        goto cleanup;
    }
    if (strstr(opus_get_version_string(), "libopus 1.4") == NULL) {
        result = 5;
        goto cleanup;
    }

cleanup:
    if (decoder) opus_decoder_destroy(decoder);
    if (encoder) opus_encoder_destroy(encoder);
    if (result == 0) puts("opus installed-package encode/decode passed");
    return result;
}
