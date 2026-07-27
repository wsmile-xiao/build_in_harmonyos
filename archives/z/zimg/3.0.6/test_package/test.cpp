#include <cstdio>
#include <cstring>

#include <zimg.h>

int main()
{
    unsigned major = 0;
    unsigned minor = 0;
    unsigned micro = 0;
    zimg_get_version_info(&major, &minor, &micro);
    if (major != 3 || minor != 0 || micro != 6) {
        std::fprintf(stderr, "unexpected zimg version: %u.%u.%u\n", major, minor, micro);
        return 1;
    }

    unsigned api_major = 0;
    unsigned api_minor = 0;
    unsigned api = zimg_get_api_version(&api_major, &api_minor);
    if (api < ZIMG_MAKE_API_VERSION(2, 4) || api_major != 2 || api_minor < 4) {
        std::fprintf(stderr, "unexpected zimg API version: %u.%u\n", api_major, api_minor);
        return 1;
    }

    zimg_image_format format;
    std::memset(&format, 0xA5, sizeof(format));
    zimg_image_format_default(&format, ZIMG_API_VERSION);
    format.width = 16;
    format.height = 16;
    format.pixel_type = ZIMG_PIXEL_BYTE;
    format.color_family = ZIMG_COLOR_GREY;
    format.pixel_range = ZIMG_RANGE_FULL;

    zimg_graph_builder_params params;
    zimg_graph_builder_params_default(&params, ZIMG_API_VERSION);
    params.cpu_type = ZIMG_CPU_NONE;

    zimg_filter_graph *graph = zimg_filter_graph_build(&format, &format, &params);
    if (!graph) {
        char err_msg[256] = {0};
        zimg_error_code_e err = zimg_get_last_error(err_msg, sizeof(err_msg));
        std::fprintf(stderr, "zimg_filter_graph_build failed: %d %s\n", err, err_msg);
        return 1;
    }

    size_t tmp_size = 0;
    zimg_error_code_e err = zimg_filter_graph_get_tmp_size(graph, &tmp_size);
    zimg_filter_graph_free(graph);
    if (err != ZIMG_ERROR_SUCCESS) {
        std::fprintf(stderr, "zimg_filter_graph_get_tmp_size failed: %d\n", err);
        return 1;
    }

    std::printf("zimg %u.%u.%u API %u.%u smoke test passed\n",
                major, minor, micro, api_major, api_minor);
    return 0;
}
