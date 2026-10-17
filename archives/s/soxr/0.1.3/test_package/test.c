#include <stdio.h>
#include <soxr.h>
int main(void) {
    soxr_error_t error = NULL;
    soxr_t resampler = soxr_create(44100.0, 48000.0, 2, &error, NULL, NULL, NULL);
    if (error) { fprintf(stderr, "soxr_create failed: %s\n", soxr_strerror(error)); return 1; }
    if (!resampler) { fprintf(stderr, "soxr_create returned NULL\n"); return 1; }
    const float in_buf[8] = {0};
    float out_buf[16] = {0};
    size_t in_done = 0, out_done = 0;
    error = soxr_process(resampler, in_buf, 4, &in_done, out_buf, 16, &out_done);
    if (error) { fprintf(stderr, "soxr_process failed: %s\n", soxr_strerror(error)); soxr_delete(resampler); return 1; }
    soxr_delete(resampler);
    const char *ver = soxr_version();
    printf("soxr version: %s\n", ver);
    printf("soxr test: OK (in_done=%zu, out_done=%zu)\n", in_done, out_done);
    return 0;
}
