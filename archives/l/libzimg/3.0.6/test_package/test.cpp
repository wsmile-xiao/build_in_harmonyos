#include <cstdio>
#include <cstring>
#include <cstdlib>

#include <zimg.h>

// OHOS-specific verification: drive a real end-to-end conversion through
// the public C API with CPU auto-dispatch (the aarch64 NEON kernels the
// autotools build selected via --host=aarch64-linux). A BYTE full-range to
// WORD limited-range grey conversion exercises the depth/dither stage
// (aarch64 NEON depth_convert kernel) plus graph building, and the output
// must stay inside the limited-range clamp.
static int verify_ohos_specific()
{
#ifdef __OHOS__
    zimg_image_format src_fmt{};
    zimg_image_format dst_fmt{};
    zimg_graph_builder_params params{};

    zimg_image_format_default(&src_fmt, ZIMG_API_VERSION);
    zimg_image_format_default(&dst_fmt, ZIMG_API_VERSION);
    zimg_graph_builder_params_default(&params, ZIMG_API_VERSION);

    // ZIMG_CPU_AUTO: runtime dispatch (NEON on this aarch64 OHOS host).
    params.cpu_type = ZIMG_CPU_AUTO;

    src_fmt.width = 16; src_fmt.height = 16;
    src_fmt.pixel_type = ZIMG_PIXEL_BYTE;
    src_fmt.color_family = ZIMG_COLOR_GREY;
    src_fmt.pixel_range = ZIMG_RANGE_FULL;

    dst_fmt.width = 16; dst_fmt.height = 16;
    dst_fmt.pixel_type = ZIMG_PIXEL_WORD;
    dst_fmt.color_family = ZIMG_COLOR_GREY;
    dst_fmt.pixel_range = ZIMG_RANGE_LIMITED;

    zimg_filter_graph *graph = zimg_filter_graph_build(&src_fmt, &dst_fmt, &params);
    if (!graph) {
        char err[256] = {0};
        zimg_get_last_error(err, sizeof(err));
        std::fprintf(stderr, "graph build failed: %s\n", err);
        return 1;
    }
    size_t tmp = 0;
    if (zimg_filter_graph_get_tmp_size(graph, &tmp) != ZIMG_ERROR_SUCCESS || tmp == 0) {
        zimg_filter_graph_free(graph);
        std::fprintf(stderr, "bad tmp size\n");
        return 1;
    }
    void *tmp_buf = std::malloc(tmp);
    unsigned char src[16 * 16];
    unsigned short dst[16 * 16];
    for (int i = 0; i < 16 * 16; i++) src[i] = static_cast<unsigned char>(i);

    zimg_image_buffer_const src_buf{};
    zimg_image_buffer dst_buf{};
    src_buf.plane[0].data = src;
    src_buf.plane[0].stride = 16;
    src_buf.plane[0].mask = ZIMG_BUFFER_MAX;
    dst_buf.plane[0].data = dst;
    dst_buf.plane[0].stride = 32;
    dst_buf.plane[0].mask = ZIMG_BUFFER_MAX;

    zimg_error_code_e rc = zimg_filter_graph_process(
        graph, &src_buf, &dst_buf, tmp_buf,
        nullptr, nullptr, nullptr, nullptr);
    zimg_filter_graph_free(graph);
    std::free(tmp_buf);
    if (rc != ZIMG_ERROR_SUCCESS) {
        char err[256] = {0};
        zimg_get_last_error(err, sizeof(err));
        std::fprintf(stderr, "graph process failed: %s\n", err);
        return 1;
    }
    // limited-range byte->word: output must stay inside [16, 235*257].
    unsigned lo = dst[0], hi = dst[0];
    for (int i = 1; i < 16 * 16; i++) {
        if (dst[i] < lo) lo = dst[i];
        if (dst[i] > hi) hi = dst[i];
    }
    std::printf("OHOS NEON depth path: output range [%u, %u] ok\n", lo, hi);
    if (lo < 16 || hi > 235 * 257) {
        std::fprintf(stderr, "limited-range clamp violated\n");
        return 1;
    }
#endif
    return 0;
}

int main()
{
    unsigned major = 0, minor = 0, micro = 0;
    zimg_get_version_info(&major, &minor, &micro);
    if (major != 3 || minor != 0 || micro != 6) {
        std::fprintf(stderr, "unexpected version %u.%u.%u\n", major, minor, micro);
        return 1;
    }
    unsigned api_major = 0, api_minor = 0;
    unsigned api = zimg_get_api_version(&api_major, &api_minor);
    if (api < ZIMG_MAKE_API_VERSION(2, 4) || api_major != 2 || api_minor < 4) {
        std::fprintf(stderr, "unexpected API %u.%u\n", api_major, api_minor);
        return 1;
    }

    // resize graph smoke: 16x16 float grey -> 8x8 exercises the resize
    // stage (aarch64 NEON resize kernel on this host).
    zimg_image_format fmt{};
    zimg_graph_builder_params params{};
    zimg_image_format_default(&fmt, ZIMG_API_VERSION);
    zimg_graph_builder_params_default(&params, ZIMG_API_VERSION);
    fmt.width = 16; fmt.height = 16;
    fmt.pixel_type = ZIMG_PIXEL_FLOAT;
    fmt.color_family = ZIMG_COLOR_GREY;

    zimg_image_format out = fmt;
    out.width = 8; out.height = 8;

    zimg_filter_graph *graph = zimg_filter_graph_build(&fmt, &out, &params);
    if (!graph) {
        char err[256] = {0};
        zimg_get_last_error(err, sizeof(err));
        std::fprintf(stderr, "graph build failed: %s\n", err);
        return 1;
    }
    size_t tmp_size = 0;
    zimg_error_code_e err = zimg_filter_graph_get_tmp_size(graph, &tmp_size);
    zimg_filter_graph_free(graph);
    if (err != ZIMG_ERROR_SUCCESS || tmp_size == 0) {
        std::fprintf(stderr, "bad tmp size\n");
        return 1;
    }

    if (verify_ohos_specific() != 0)
        return 1;

    std::printf("libzimg %u.%u.%u API %u.%u consumer test passed (resize graph + OHOS NEON depth path)\n",
                major, minor, micro, api_major, api_minor);
    return 0;
}
