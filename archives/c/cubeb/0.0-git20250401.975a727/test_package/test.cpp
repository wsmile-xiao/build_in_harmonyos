#include <cubeb/cubeb.h>
#include <cstdio>
#include <cstdlib>
#include <cstring>

int main(void) {
    cubeb *ctx = NULL;
    int rv = cubeb_init(&ctx, "ConanTestCubeb", NULL);
    if (rv == CUBEB_OK) {
        printf("cubeb_init: OK (backend available)\n");

        cubeb_stream_params params;
        memset(&params, 0, sizeof(params));
        params.format = CUBEB_SAMPLE_S16NE;
        params.rate = 44100;
        params.channels = 1;
        params.layout = CUBEB_LAYOUT_MONO;

        uint32_t latency_ms = 0;
        rv = cubeb_get_min_latency(ctx, &params, &latency_ms);
        if (rv == CUBEB_OK) {
            printf("cubeb_get_min_latency: OK (%u ms)\n", latency_ms);
        } else {
            printf("cubeb_get_min_latency: not available (rv=%d) — expected on headless OHOS\n", rv);
        }

        uint32_t rate = 0;
        rv = cubeb_get_preferred_sample_rate(ctx, &rate);
        if (rv == CUBEB_OK) {
            printf("cubeb_get_preferred_sample_rate: OK (%u Hz)\n", rate);
        } else {
            printf("cubeb_get_preferred_sample_rate: not available (rv=%d) — expected on headless OHOS\n", rv);
        }

        cubeb_destroy(ctx);
        printf("cubeb_destroy: OK\n");
        printf("test cubeb: PASS\n");
    } else {
        printf("cubeb_init returned %d (no audio backend on headless OHOS — library OK)\n", rv);
        printf("test cubeb: PASS (library linked, API available)\n");
    }
    return 0;
}
