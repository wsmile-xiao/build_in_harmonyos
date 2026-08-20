#include <sndfile.h>

#include <stdio.h>
#include <string.h>

int main(void) {
    static const char *path = "libsndfile-consumer-roundtrip.wav";
    static const short samples[] = {
        0, 1000, -1000, 32767, -32768, 42, -42, 7
    };
    short decoded[sizeof(samples) / sizeof(samples[0])] = {0};
    SF_INFO info = {0};
    SNDFILE *file = NULL;
    const char *version = sf_version_string();

    if (version == NULL || version[0] == '\0') {
        fprintf(stderr, "libsndfile returned an empty version string\n");
        return 1;
    }

    info.samplerate = 44100;
    info.channels = 2;
    info.format = SF_FORMAT_WAV | SF_FORMAT_PCM_16;
    if (!sf_format_check(&info)) {
        fprintf(stderr, "libsndfile rejected a standard WAV/PCM format\n");
        return 1;
    }

    remove(path);
    file = sf_open(path, SFM_WRITE, &info);
    if (file == NULL) {
        fprintf(stderr, "sf_open write failed: %s\n", sf_strerror(NULL));
        return 1;
    }
    if (sf_writef_short(file, samples, 4) != 4 || sf_close(file) != 0) {
        fprintf(stderr, "WAV write failed\n");
        remove(path);
        return 1;
    }

    memset(&info, 0, sizeof(info));
    file = sf_open(path, SFM_READ, &info);
    if (file == NULL) {
        fprintf(stderr, "sf_open read failed: %s\n", sf_strerror(NULL));
        remove(path);
        return 1;
    }
    if (info.samplerate != 44100 || info.channels != 2 || info.frames != 4) {
        fprintf(stderr, "unexpected WAV metadata\n");
        sf_close(file);
        remove(path);
        return 1;
    }
    if (sf_readf_short(file, decoded, 4) != 4 || sf_close(file) != 0) {
        fprintf(stderr, "WAV read failed\n");
        remove(path);
        return 1;
    }
    if (memcmp(samples, decoded, sizeof(samples)) != 0) {
        fprintf(stderr, "PCM round trip mismatch\n");
        remove(path);
        return 1;
    }
    if (remove(path) != 0) {
        fprintf(stderr, "unable to remove round-trip file\n");
        return 1;
    }

    printf("PASS libsndfile %s WAV/PCM round trip\n", version);
    return 0;
}
