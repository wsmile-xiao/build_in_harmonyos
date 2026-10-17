/* Consumer test for onednn/3.12.1 on HarmonyOS aarch64.
 *
 * Goes beyond a load-and-version check: it runs a real softmax forward on the
 * CPU engine, which exercises the AArch64 JIT kernel-generation path and the
 * OpenMP runtime that the recipe links against.
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <oneapi/dnnl/dnnl.h>
#include <oneapi/dnnl/dnnl_version.h>

static int g_total;
static int g_failed;

#define CHECK(cond, what) \
    do { \
        ++g_total; \
        if (!(cond)) { \
            ++g_failed; \
            printf("FAIL(%d): %s\n", g_total, (what)); \
        } else { \
            printf("ok(%d): %s\n", g_total, (what)); \
        } \
    } while (0)

#define NDIMS 4
static const dnnl_dims_t dims = {2, 3, 4, 4};
static const dnnl_dims_t strides = {48, 16, 4, 1};
static const int nelem = 2 * 3 * 4 * 4;
static const int axis = 1;

static float *in_buf;
static float *out_buf;

static size_t off(int n, int c, int h, int w) {
    return (size_t)n * strides[0] + (size_t)c * strides[1] + (size_t)h * strides[2]
            + (size_t)w * strides[3];
}

int main(void) {
    dnnl_engine_t engine = NULL;
    CHECK(dnnl_engine_create(&engine, dnnl_cpu, 0) == dnnl_success && engine != NULL,
            "cpu engine created");
    if (engine == NULL) return 1;

    const dnnl_version_t *ver = dnnl_version();
    CHECK(ver != NULL, "dnnl_version() available");
    CHECK(ver != NULL && ver->major == DNNL_VERSION_MAJOR && ver->minor == DNNL_VERSION_MINOR
                    && ver->patch == DNNL_VERSION_PATCH,
            "runtime .so version matches packaged headers");

    dnnl_memory_desc_t md = NULL;
    CHECK(dnnl_memory_desc_create_with_strides(&md, NDIMS, dims, dnnl_f32, strides)
                            == dnnl_success
                    && md != NULL,
            "f32 memory descriptor created");
    CHECK(md != NULL && dnnl_memory_desc_get_size(md) == (size_t)nelem * sizeof(float),
            "memory descriptor byte size");

    in_buf = (float *) malloc((size_t) nelem * sizeof(float));
    out_buf = (float *) malloc((size_t) nelem * sizeof(float));
    if (in_buf == NULL || out_buf == NULL) return 1;
    for (int i = 0; i < nelem; ++i) in_buf[i] = (float) i * 0.01f - 0.5f;
    memset(out_buf, 0, (size_t) nelem * sizeof(float));

    dnnl_primitive_desc_t pd = NULL;
    CHECK(dnnl_softmax_forward_primitive_desc_create(&pd, engine, dnnl_forward,
                    dnnl_softmax_accurate, md, md, axis, NULL)
                            == dnnl_success
                    && pd != NULL,
            "softmax forward primitive descriptor");

    dnnl_primitive_t prim = NULL;
    if (pd != NULL) {
        CHECK(dnnl_primitive_create(&prim, pd) == dnnl_success && prim != NULL,
                "softmax forward primitive created");
    }

    dnnl_stream_t stream = NULL;
    if (prim != NULL) {
        CHECK(dnnl_stream_create(&stream, engine, dnnl_stream_default_flags)
                                == dnnl_success
                        && stream != NULL,
                "cpu stream created");
    }

    dnnl_memory_t src_mem = NULL, dst_mem = NULL, scratch_mem = NULL;
    void *scratch = NULL;
    size_t scratch_size = 0;
    if (stream != NULL) {
        const_dnnl_memory_desc_t scratch_md
                = dnnl_primitive_desc_query_md(pd, dnnl_query_scratchpad_md, 0);
        if (scratch_md != NULL) scratch_size = dnnl_memory_desc_get_size(scratch_md);
        if (scratch_size > 0) {
            scratch = malloc(scratch_size);
            if (scratch != NULL
                    && dnnl_memory_create(&scratch_mem, scratch_md, engine, scratch)
                                    != dnnl_success) {
                scratch_mem = NULL;
            }
        }
        CHECK(dnnl_memory_create(&src_mem, md, engine, in_buf) == dnnl_success
                        && dnnl_memory_create(&dst_mem, md, engine, out_buf) == dnnl_success
                        && src_mem != NULL && dst_mem != NULL,
                "caller buffers bound as dnnl_memory");
    }

    if (src_mem != NULL && dst_mem != NULL) {
        dnnl_exec_arg_t args[4];
        int nargs = 0;
        args[nargs].arg = DNNL_ARG_SRC;
        args[nargs++].memory = src_mem;
        args[nargs].arg = DNNL_ARG_DST;
        args[nargs++].memory = dst_mem;
        if (scratch_mem != NULL) {
            args[nargs].arg = DNNL_ARG_SCRATCHPAD;
            args[nargs++].memory = scratch_mem;
        }
        CHECK(dnnl_primitive_execute(prim, stream, nargs, args) == dnnl_success,
                "softmax forward executed on cpu/aarch64");
    }

    if (g_failed == 0) {
        int bad_sum = 0;
        for (int n = 0; n < 2; ++n) {
            for (int h = 0; h < 4; ++h) {
                for (int w = 0; w < 4; ++w) {
                    float sum = 0.0f;
                    for (int c = 0; c < 3; ++c) sum += out_buf[off(n, c, h, w)];
                    if (fabsf(sum - 1.0f) > 1e-4f) bad_sum = 1;
                }
            }
        }
        CHECK(bad_sum == 0, "every channel slice sums to 1");

        float max00 = in_buf[off(0, 0, 0, 0)];
        float max10 = in_buf[off(1, 0, 0, 0)];
        float denom = 0.0f;
        for (int c = 0; c < 3; ++c) denom += expf(in_buf[off(0, c, 0, 0)] - max00);
        float want = expf(in_buf[off(0, 1, 0, 0)] - max00) / denom;
        float want1 = expf(in_buf[off(1, 1, 0, 0)] - max10)
                / (expf(in_buf[off(1, 0, 0, 0)] - max10)
                        + expf(in_buf[off(1, 1, 0, 0)] - max10)
                        + expf(in_buf[off(1, 2, 0, 0)] - max10));
        CHECK(fabsf(out_buf[off(0, 1, 0, 0)] - want) < 1e-5f
                        && fabsf(out_buf[off(1, 1, 0, 0)] - want1) < 1e-5f,
                "outputs match a locally computed reference");
    }

    if (scratch_mem != NULL) dnnl_memory_destroy(scratch_mem);
    if (src_mem != NULL) dnnl_memory_destroy(src_mem);
    if (dst_mem != NULL) dnnl_memory_destroy(dst_mem);
    free(scratch);
    if (stream != NULL) dnnl_stream_destroy(stream);
    if (prim != NULL) dnnl_primitive_destroy(prim);
    if (pd != NULL) dnnl_primitive_desc_destroy(pd);
    if (md != NULL) dnnl_memory_desc_destroy(md);
    dnnl_engine_destroy(engine);
    free(in_buf);
    free(out_buf);

    printf("onednn version=%d.%d.%d engine=cpu ok: %d/%d assertions passed\n",
            ver->major, ver->minor, ver->patch, g_total - g_failed, g_total);
    return g_failed != 0;
}
