#include <stdio.h>
#include <string.h>

#include <aften/aften.h>

#define CHECK(condition, message) \
    do { \
        if (!(condition)) { \
            fprintf(stderr, "FAIL: %s\n", message); \
            return __LINE__; \
        } \
    } while (0)

int main(void)
{
    AftenContext context;
    unsigned char frame[A52_MAX_CODED_FRAME_SIZE];
    float samples[A52_SAMPLES_PER_FRAME * 2] = {0.0f};
    int frame_size;

    CHECK(strcmp(aften_get_version(), "0.0.8") == 0, "exact library version");

    aften_set_defaults(&context);
    context.channels = 2;
    context.acmod = 2;
    context.lfe = 0;
    context.samplerate = 12345;
    context.sample_format = A52_SAMPLE_FMT_FLT;
    CHECK(aften_encode_init(&context) != 0, "invalid sample rate is rejected");
    aften_encode_close(&context);

    aften_set_defaults(&context);
    context.channels = 2;
    context.acmod = 2;
    context.lfe = 0;
    context.samplerate = 48000;
    context.sample_format = A52_SAMPLE_FMT_FLT;
    context.system.n_threads = 1;
    CHECK(aften_encode_init(&context) == 0, "valid encoder initializes");
    frame_size = aften_encode_frame(&context, frame, samples);
    CHECK(frame_size > 0, "silent stereo frame is encoded");
    CHECK(frame_size <= A52_MAX_CODED_FRAME_SIZE, "frame fits public maximum");
    CHECK(frame[0] == 0x0b && frame[1] == 0x77, "AC-3 sync word is present");
    aften_encode_close(&context);

    printf("PASS: aften encoded %d-byte AC-3 frame\n", frame_size);
    return 0;
}
