/*
 * 消费者侧 dummy OpenCL 层 —— 最小可用的 layer 实现。
 *
 * loader（ocl_icd_loader.c::__initLayer）加载层时只要求两个符号：
 *   - clGetLayerInfo：回答 CL_LAYER_API_VERSION / CL_LAYER_NAME；
 *   - clInitLayer：拿到下游 dispatch 表后返回自己的 dispatch 表与条目数。
 * 这里实现一个“透传层”：把 loader 给的 target_dispatch 原样返回，
 * 使被测二进制 cllayerinfo 能打印出本层的 API 版本与名字，
 * 与上游 tests/testsuite-standard.at:103 期望的输出一致：
 *
 *   <libtestlayer.so>:
 *   	CL_LAYER_API_VERSION: 100
 *   	CL_LAYER_NAME: dummylayer
 */
#include <CL/cl.h>
#include <CL/cl_layer.h>

#include <string.h>

/* 与上游 dummy 层同名，便于断言与上游用例对齐 */
static const char layer_name[] = "dummylayer";

CL_API_ENTRY cl_int CL_API_CALL
clGetLayerInfo(cl_layer_info param_name,
               size_t param_value_size,
               void *param_value,
               size_t *param_value_size_ret)
{
    switch (param_name) {
    case CL_LAYER_API_VERSION: {
        cl_layer_api_version version = CL_LAYER_API_VERSION_100;
        if (param_value_size_ret) {
            *param_value_size_ret = sizeof(version);
        }
        if (param_value) {
            if (param_value_size < sizeof(version)) {
                return CL_INVALID_VALUE;
            }
            memcpy(param_value, &version, sizeof(version));
        }
        return CL_SUCCESS;
    }
    case CL_LAYER_NAME: {
        /* cllayerinfo 先以 size 0 查询长度（param_value == NULL），再按长度取值，
         * 因此这里返回含结尾 NUL 的完整长度。 */
        size_t size = sizeof(layer_name);
        if (param_value_size_ret) {
            *param_value_size_ret = size;
        }
        if (param_value) {
            if (param_value_size < size) {
                return CL_INVALID_VALUE;
            }
            memcpy(param_value, layer_name, size);
        }
        return CL_SUCCESS;
    }
    default:
        return CL_INVALID_VALUE;
    }
}

CL_API_ENTRY cl_int CL_API_CALL
clInitLayer(cl_uint num_entries,
            const cl_icd_dispatch *target_dispatch,
            cl_uint *num_entries_ret,
            const cl_icd_dispatch **layer_dispatch_ret)
{
    if (target_dispatch == NULL) {
        return CL_INVALID_VALUE;
    }
    /* 透传：loader 要求返回非空 dispatch 表且条目数 > 0
     * （ocl_icd_loader.c: err != CL_SUCCESS || !layer_dispatch || !layer_dispatch_num_entries） */
    if (num_entries_ret) {
        *num_entries_ret = num_entries;
    }
    if (layer_dispatch_ret) {
        *layer_dispatch_ret = target_dispatch;
    }
    return CL_SUCCESS;
}
