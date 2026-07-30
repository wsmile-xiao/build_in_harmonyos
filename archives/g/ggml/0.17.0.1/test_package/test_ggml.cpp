#include <ggml-cpu.h>
#include <ggml.h>

#include <cmath>
#include <cstdio>
#include <cstring>

int main() {
    const size_t context_size =
        3 * ggml_tensor_overhead() + ggml_graph_overhead() + 1024;
    ggml_init_params params{};
    params.mem_size = context_size;
    params.mem_buffer = nullptr;
    params.no_alloc = false;

    ggml_context *context = ggml_init(params);
    if (!context) {
        std::fprintf(stderr, "ggml_init failed\n");
        return 1;
    }

    ggml_tensor *lhs = ggml_new_tensor_1d(context, GGML_TYPE_F32, 4);
    ggml_tensor *rhs = ggml_new_tensor_1d(context, GGML_TYPE_F32, 4);
    if (!lhs || !rhs) {
        std::fprintf(stderr, "ggml_new_tensor_1d failed\n");
        ggml_free(context);
        return 1;
    }

    const float lhs_values[] = {1.0f, 2.0f, 3.0f, 4.0f};
    const float rhs_values[] = {4.0f, 3.0f, 2.0f, 1.0f};
    std::memcpy(lhs->data, lhs_values, sizeof(lhs_values));
    std::memcpy(rhs->data, rhs_values, sizeof(rhs_values));

    ggml_tensor *sum = ggml_add(context, lhs, rhs);
    if (!sum) {
        std::fprintf(stderr, "ggml_add failed\n");
        ggml_free(context);
        return 1;
    }

    ggml_cgraph *graph = ggml_new_graph(context);
    if (!graph) {
        std::fprintf(stderr, "ggml_new_graph failed\n");
        ggml_free(context);
        return 1;
    }

    ggml_build_forward_expand(graph, sum);
    if (ggml_graph_compute_with_ctx(context, graph, 1) != GGML_STATUS_SUCCESS) {
        std::fprintf(stderr, "ggml_graph_compute_with_ctx failed\n");
        ggml_free(context);
        return 1;
    }

    const float *result = ggml_get_data_f32(sum);
    const float expected[] = {5.0f, 5.0f, 5.0f, 5.0f};
    for (int i = 0; i < 4; ++i) {
        if (std::fabs(result[i] - expected[i]) > 1e-5f) {
            std::fprintf(stderr, "unexpected result at %d: %f\n", i, result[i]);
            ggml_free(context);
            return 1;
        }
    }

    std::printf("ggml tensor API and CPU graph test passed\n");
    ggml_free(context);
    return 0;
}
