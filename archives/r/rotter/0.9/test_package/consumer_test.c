/*
 * rotter 0.9 — HarmonyOS consumer-use feasibility test.
 *
 * A third-party C consumer compiles and runs against the dependency stack
 * rotter is built with, exercising each output-format path rotter supports:
 *   1. libsndfile — WAV write/read roundtrip (rotter's PCM output formats)
 *   2. lame       — MP3 init/encode/flush   (rotter's default mp3 format)
 *   3. twolame    — MP2 init/encode/flush   (rotter's mp2 format)
 *
 * JACK is covered by the packaged rotter binary itself (linked to libjack),
 * which the test_package conanfile.py executes as a --help smoke test.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <sndfile.h>
#include <lame/lame.h>
#include <twolame.h>

static int failures = 0;

#define CHECK(cond, name) \
    do { \
        if (cond) { printf("[PASS] %s\n", name); } \
        else { printf("[FAIL] %s\n", name); failures++; } \
    } while (0)

static void test_sndfile_wav_roundtrip(void) {
    const char *path = "rotter_consumer_test.wav";
    SF_INFO info;
    SNDFILE *f;
    short buf[2048];
    short back[2048];
    int i;

    memset(&info, 0, sizeof(info));
    info.samplerate = 44100;
    info.channels = 2;
    info.format = SF_FORMAT_WAV | SF_FORMAT_PCM_16;

    f = sf_open(path, SFM_WRITE, &info);
    CHECK(f != NULL, "libsndfile: sf_open WAV writer");
    if (f == NULL)
        return;

    for (i = 0; i < 1024; i++) {
        buf[2 * i] = (short)(i * 7);
        buf[2 * i + 1] = (short)(-i * 7);
    }
    CHECK(sf_writef_short(f, buf, 1024) == 1024, "libsndfile: sf_writef_short 1024 frames");
    sf_close(f);

    memset(&info, 0, sizeof(info));
    f = sf_open(path, SFM_READ, &info);
    CHECK(f != NULL, "libsndfile: sf_open WAV reader");
    if (f == NULL)
        return;
    CHECK(sf_readf_short(f, back, 1024) == 1024, "libsndfile: sf_readf_short 1024 frames");
    sf_close(f);
    CHECK(back[0] == 0 && back[1] == 0 && back[2] == 7 && back[3] == -7,
          "libsndfile: WAV content roundtrip matches");
    remove(path);
}

static void test_lame_mp3_encode(void) {
    lame_t gfp;
    short pcm[2 * 1152];
    unsigned char mp3[5 * 1152];
    int ret;

    gfp = lame_init();
    CHECK(gfp != NULL, "lame: lame_init");
    if (gfp == NULL)
        return;

    CHECK(get_lame_version() != NULL && get_lame_version()[0] != '\0',
          "lame: get_lame_version");

    lame_set_num_channels(gfp, 2);
    lame_set_in_samplerate(gfp, 44100);
    lame_set_brate(gfp, 128);
    CHECK(lame_init_params(gfp) >= 0, "lame: lame_init_params");

    memset(pcm, 0, sizeof(pcm));
    ret = lame_encode_buffer_interleaved(gfp, pcm, 1152, mp3, sizeof(mp3));
    CHECK(ret >= 0, "lame: lame_encode_buffer_interleaved 1152 frames");
    ret = lame_encode_flush(gfp, mp3, sizeof(mp3));
    CHECK(ret >= 0, "lame: lame_encode_flush");
    lame_close(gfp);
}

static void test_twolame_mp2_encode(void) {
    twolame_options *opts;
    short pcm[2 * 1152];
    unsigned char mp2[5 * 1152];
    int ret;

    opts = twolame_init();
    CHECK(opts != NULL, "twolame: twolame_init");
    if (opts == NULL)
        return;

    twolame_set_num_channels(opts, 2);
    twolame_set_in_samplerate(opts, 44100);
    twolame_set_bitrate(opts, 192);
    CHECK(twolame_init_params(opts) == 0, "twolame: twolame_init_params");

    memset(pcm, 0, sizeof(pcm));
    ret = twolame_encode_buffer(opts, pcm, pcm, 1152, mp2, sizeof(mp2));
    CHECK(ret >= 0, "twolame: twolame_encode_buffer 1152 frames");
    ret = twolame_encode_flush(opts, mp2, sizeof(mp2));
    CHECK(ret >= 0, "twolame: twolame_encode_flush");
    twolame_close(&opts);
}

int main(void) {
    printf("rotter 0.9 HarmonyOS consumer test — dependency stack use\n");
    test_sndfile_wav_roundtrip();
    test_lame_mp3_encode();
    test_twolame_mp2_encode();
    printf("rotter_consumer_test: %s (%d failure(s))\n",
           failures == 0 ? "PASS" : "FAIL", failures);
    return failures == 0 ? 0 : 1;
}
