/* Consumer test for libfdk 2.0.3 (Fraunhofer FDK AAC).
 *
 * Four deterministic cases (mirrors upstream test/run-test.sh stereo+mono):
 *   encoder            - open AAC-LC encoder, set params, init, close
 *   decoder            - open RAW decoder, close
 *   roundtrip-mono     - synth 1ch square-wave PCM, AAC-LC 64k encode,
 *                        RAW decode, verify output non-empty and sane
 *   roundtrip-stereo   - same for 2ch
 *
 * No file I/O, no network, no ffmpeg. Square wave avoids libm dependency.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>

#include <fdk-aac/aacenc_lib.h>
#include <fdk-aac/aacdecoder_lib.h>

static void fill_square(int16_t *buf, int samples, int channels, int rate)
{
    int period = rate / 440;
    if (period < 2)
        period = 2;
    for (int i = 0; i < samples; i++) {
        int phase = (i / channels) % period;
        int16_t v = (phase < period / 2) ? 8000 : -8000;
        buf[i] = v;
    }
}

static int test_encoder(void)
{
    HANDLE_AACENCODER enc = NULL;
    if (aacEncOpen(&enc, 0, 2) != AACENC_OK) {
        fprintf(stderr, "encoder: aacEncOpen failed\n");
        return 1;
    }
    if (aacEncoder_SetParam(enc, AACENC_AOT, 2) != AACENC_OK) {
        fprintf(stderr, "encoder: set AOT failed\n");
        aacEncClose(&enc);
        return 1;
    }
    if (aacEncoder_SetParam(enc, AACENC_SAMPLERATE, 44100) != AACENC_OK) {
        fprintf(stderr, "encoder: set samplerate failed\n");
        aacEncClose(&enc);
        return 1;
    }
    if (aacEncoder_SetParam(enc, AACENC_CHANNELMODE, MODE_2) != AACENC_OK) {
        fprintf(stderr, "encoder: set channelmode failed\n");
        aacEncClose(&enc);
        return 1;
    }
    if (aacEncoder_SetParam(enc, AACENC_CHANNELORDER, 1) != AACENC_OK) {
        fprintf(stderr, "encoder: set channelorder failed\n");
        aacEncClose(&enc);
        return 1;
    }
    if (aacEncoder_SetParam(enc, AACENC_BITRATE, 64000) != AACENC_OK) {
        fprintf(stderr, "encoder: set bitrate failed\n");
        aacEncClose(&enc);
        return 1;
    }
    if (aacEncoder_SetParam(enc, AACENC_TRANSMUX, 0) != AACENC_OK) {
        fprintf(stderr, "encoder: set transmux failed\n");
        aacEncClose(&enc);
        return 1;
    }
    if (aacEncoder_SetParam(enc, AACENC_AFTERBURNER, 1) != AACENC_OK) {
        fprintf(stderr, "encoder: set afterburner failed\n");
        aacEncClose(&enc);
        return 1;
    }
    if (aacEncEncode(enc, NULL, NULL, NULL, NULL) != AACENC_OK) {
        fprintf(stderr, "encoder: init encode failed\n");
        aacEncClose(&enc);
        return 1;
    }
    AACENC_InfoStruct info = {0};
    if (aacEncInfo(enc, &info) != AACENC_OK) {
        fprintf(stderr, "encoder: aacEncInfo failed\n");
        aacEncClose(&enc);
        return 1;
    }
    if (info.frameLength <= 0 || info.confSize <= 0) {
        fprintf(stderr, "encoder: bad info frameLength=%d confSize=%d\n",
                info.frameLength, (int)info.confSize);
        aacEncClose(&enc);
        return 1;
    }
    aacEncClose(&enc);
    printf("PASS: encoder open/setparam/init/close (frameLength=%d confSize=%d)\n",
           info.frameLength, (int)info.confSize);
    return 0;
}

static int test_decoder(void)
{
    HANDLE_AACDECODER dec = aacDecoder_Open(TT_MP4_RAW, 1);
    if (dec == NULL) {
        fprintf(stderr, "decoder: aacDecoder_Open failed\n");
        return 1;
    }
    aacDecoder_Close(dec);
    printf("PASS: decoder open/close\n");
    return 0;
}

static int test_roundtrip(int channels)
{
    const int rate = 44100;
    HANDLE_AACENCODER enc = NULL;
    CHANNEL_MODE mode = (channels == 1) ? MODE_1 : MODE_2;
    if (aacEncOpen(&enc, 0, (unsigned int)channels) != AACENC_OK) {
        fprintf(stderr, "roundtrip(ch=%d): encoder open failed\n", channels);
        return 1;
    }
    aacEncoder_SetParam(enc, AACENC_AOT, 2);
    aacEncoder_SetParam(enc, AACENC_SAMPLERATE, (unsigned int)rate);
    aacEncoder_SetParam(enc, AACENC_CHANNELMODE, mode);
    aacEncoder_SetParam(enc, AACENC_CHANNELORDER, 1);
    aacEncoder_SetParam(enc, AACENC_BITRATE, 64000);
    aacEncoder_SetParam(enc, AACENC_TRANSMUX, 0);
    aacEncoder_SetParam(enc, AACENC_AFTERBURNER, 1);
    if (aacEncEncode(enc, NULL, NULL, NULL, NULL) != AACENC_OK) {
        fprintf(stderr, "roundtrip(ch=%d): encoder init failed\n", channels);
        aacEncClose(&enc);
        return 1;
    }
    AACENC_InfoStruct info = {0};
    if (aacEncInfo(enc, &info) != AACENC_OK) {
        fprintf(stderr, "roundtrip(ch=%d): aacEncInfo failed\n", channels);
        aacEncClose(&enc);
        return 1;
    }

    HANDLE_AACDECODER dec = aacDecoder_Open(TT_MP4_RAW, 1);
    if (dec == NULL) {
        fprintf(stderr, "roundtrip(ch=%d): decoder open failed\n", channels);
        aacEncClose(&enc);
        return 1;
    }
    {
        UCHAR *conf = info.confBuf;
        UINT confSize = info.confSize;
        UCHAR *bufs[] = {conf};
        if (aacDecoder_ConfigRaw(dec, bufs, &confSize) != AAC_DEC_OK) {
            fprintf(stderr, "roundtrip(ch=%d): ConfigRaw failed\n", channels);
            aacDecoder_Close(dec);
            aacEncClose(&enc);
            return 1;
        }
    }
    aacDecoder_SetParam(dec, AAC_CONCEAL_METHOD, 1);
    aacDecoder_SetParam(dec, AAC_PCM_LIMITER_ENABLE, 0);

    int frameSamples = channels * info.frameLength;
    int16_t *pcm = (int16_t *)malloc((size_t)frameSamples * sizeof(int16_t));
    if (!pcm) {
        aacDecoder_Close(dec);
        aacEncClose(&enc);
        return 1;
    }
    fill_square(pcm, frameSamples, channels, rate);

    int totalOut = 0;
    int totalDecoded = 0;
    for (int f = 0; f < 4; f++) {
        AACENC_BufDesc inBuf = {0}, outBuf = {0};
        AACENC_InArgs inArgs = {0};
        AACENC_OutArgs outArgs = {0};
        int inId = IN_AUDIO_DATA, outId = OUT_BITSTREAM_DATA;
        int inSize = frameSamples * 2, inElem = 2;
        void *inPtr = pcm;
        uint8_t outArr[20480];
        void *outPtr = outArr;
        int outSize = (int)sizeof(outArr), outElem = 1;

        inBuf.numBufs = 1;
        inBuf.bufs = &inPtr;
        inBuf.bufferIdentifiers = &inId;
        inBuf.bufSizes = &inSize;
        inBuf.bufElSizes = &inElem;
        inArgs.numInSamples = frameSamples;
        outBuf.numBufs = 1;
        outBuf.bufs = &outPtr;
        outBuf.bufferIdentifiers = &outId;
        outBuf.bufSizes = &outSize;
        outBuf.bufElSizes = &outElem;

        AACENC_ERROR eerr = aacEncEncode(enc, &inBuf, &outBuf, &inArgs, &outArgs);
        if (eerr != AACENC_OK) {
            fprintf(stderr, "roundtrip(ch=%d): encode frame %d failed %d\n", channels, f, (int)eerr);
            free(pcm);
            aacDecoder_Close(dec);
            aacEncClose(&enc);
            return 1;
        }
        if (outArgs.numOutBytes <= 0)
            continue;
        totalOut += outArgs.numOutBytes;

        uint8_t decBuf[2048 * 8 * 2];
        uint8_t *ptr = outArr;
        int size = outArgs.numOutBytes;
        while (size > 0) {
            UINT valid = (UINT)size, bs = (UINT)size;
            uint8_t *p = ptr;
            AAC_DECODER_ERROR derr = aacDecoder_Fill(dec, &p, &bs, &valid);
            int consumed = size - (int)valid;
            ptr += consumed;
            size -= consumed;
            if (derr == AAC_DEC_NOT_ENOUGH_BITS)
                continue;
            if (derr != AAC_DEC_OK)
                break;
            derr = aacDecoder_DecodeFrame(dec, (INT_PCM *)decBuf, (int)sizeof(decBuf) / 2, 0);
            if (derr == AAC_DEC_NOT_ENOUGH_BITS)
                continue;
            if (derr != AAC_DEC_OK) {
                fprintf(stderr, "roundtrip(ch=%d): decode failed\n", channels);
                free(pcm);
                aacDecoder_Close(dec);
                aacEncClose(&enc);
                return 1;
            }
            CStreamInfo *sinfo = aacDecoder_GetStreamInfo(dec);
            if (sinfo && sinfo->numChannels == channels && sinfo->frameSize > 0)
                totalDecoded += sinfo->numChannels * sinfo->frameSize;
        }
    }
    free(pcm);
    aacDecoder_Close(dec);
    aacEncClose(&enc);

    if (totalOut <= 0) {
        fprintf(stderr, "roundtrip(ch=%d): no encoded bytes\n", channels);
        return 1;
    }
    if (totalDecoded <= 0) {
        fprintf(stderr, "roundtrip(ch=%d): no decoded samples\n", channels);
        return 1;
    }
    printf("PASS: roundtrip ch=%d encoded=%d bytes decoded=%d samples\n",
           channels, totalOut, totalDecoded);
    return 0;
}

int main(int argc, char **argv)
{
    if (argc != 2) {
        fprintf(stderr, "usage: %s encoder|decoder|roundtrip-mono|roundtrip-stereo\n", argv[0]);
        return 2;
    }
    if (strcmp(argv[1], "encoder") == 0)
        return test_encoder();
    if (strcmp(argv[1], "decoder") == 0)
        return test_decoder();
    if (strcmp(argv[1], "roundtrip-mono") == 0)
        return test_roundtrip(1);
    if (strcmp(argv[1], "roundtrip-stereo") == 0)
        return test_roundtrip(2);
    fprintf(stderr, "unknown case %s\n", argv[1]);
    return 2;
}
