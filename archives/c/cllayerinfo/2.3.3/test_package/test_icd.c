// 消费者侧 dummy OpenCL ICD（安装驱动），只为让 loader 走到层初始化。
//
// 为什么必须有它 —— ocl_icd_loader.c 的 __initClIcd 里：
//     _find_and_check_platforms(num_icds);
//     if (_num_icds == 0) { goto abort; }   // 没有可用 ICD 就直接返回
//     __initLayers();                       // 这里才去读 OPENCL_LAYERS
// 即「没有 ICD 就没有层」，只给 OPENCL_LAYERS 是无效的。上游
// tests/testsuite-standard.at 的 cllayerinfo 用例正是同时导出
// OPENCL_LAYERS 与 OCL_ICD_VENDORS，本文件复刻其中的 vendors 一侧。
//
// loader 对 ICD 的最小要求（_find_and_check_platforms）：
//   1. 库能被 dlopen（RTLD_LAZY|RTLD_LOCAL）；
//   2. 导出 clGetExtensionFunctionAddress，且能返回 clIcdGetPlatformIDsKHR；
//   3. 可导出 clGetPlatformInfo；
//   4. clIcdGetPlatformIDsKHR 返回至少 1 个平台且返回 CL_SUCCESS；
//   5. 平台对象的 dispatch 表非空 —— loader 会读 dispatch->clGetPlatformIDs
//      判断 ICD2 tag（全零即非 tag，走传统 ICD 路径）；
//   6. 平台扩展串含 cl_khr_icd，且能回答 CL_PLATFORM_ICD_SUFFIX_KHR。
#include <CL/cl.h>
#include <CL/cl_ext.h>
#include <CL/cl_icd.h>

#include <string.h>

// Khronos 头文件里的 _cl_platform_id 只有前置声明（cl.h: typedef ... * cl_platform_id），
// 结构体本身由 ICD 实现方定义：首成员必须是指向 dispatch 表的指针，loader 依此
// 取用平台的各个入口（见上面第 5 条）。
struct _cl_platform_id {
    struct _cl_icd_dispatch *dispatch;
};

// 全零 dispatch 表：clGetPlatformIDs == NULL，不等于 CL_ICD2_TAG_KHR，
// 因此 loader 按传统 ICD 路径处理（不要求 clIcdGetFunctionAddressForPlatformKHR 等）
static struct _cl_icd_dispatch dummy_dispatch;
static struct _cl_platform_id dummy_platform = {&dummy_dispatch};

#define DUMMY_ICD_SUFFIX "TEST"

static cl_int dummy_get_platform_ids(cl_uint num_entries,
                                     cl_platform_id *platforms,
                                     cl_uint *num_platforms)
{
    if (platforms == NULL && num_platforms == NULL) {
        return CL_INVALID_VALUE;
    }
    if (num_entries == 0 && platforms != NULL) {
        return CL_INVALID_VALUE;
    }
    if (num_platforms != NULL) {
        *num_platforms = 1;
    }
    if (platforms != NULL) {
        platforms[0] = &dummy_platform;
    }
    return CL_SUCCESS;
}

CL_API_ENTRY cl_int CL_API_CALL
clIcdGetPlatformIDsKHR(cl_uint num_entries,
                       cl_platform_id *platforms,
                       cl_uint *num_platforms)
{
    return dummy_get_platform_ids(num_entries, platforms, num_platforms);
}

CL_API_ENTRY cl_int CL_API_CALL
clGetPlatformInfo(cl_platform_id platform,
                  cl_platform_info param_name,
                  size_t param_value_size,
                  void *param_value,
                  size_t *param_value_size_ret)
{
    const char *value;
    size_t size;

    (void)platform;
    switch (param_name) {
    case CL_PLATFORM_PROFILE:
        value = "FULL_PROFILE";
        break;
    case CL_PLATFORM_VERSION:
        value = "OpenCL 1.2";
        break;
    case CL_PLATFORM_NAME:
        value = "DummyCL";
        break;
    case CL_PLATFORM_VENDOR:
        value = "cllayerinfo consumer test ICD";
        break;
    case CL_PLATFORM_EXTENSIONS:
        // loader 会校验扩展串里含 cl_khr_icd，否则跳过该平台
        value = "cl_khr_icd";
        break;
    case CL_PLATFORM_ICD_SUFFIX_KHR:
        value = DUMMY_ICD_SUFFIX;
        break;
    default:
        return CL_INVALID_VALUE;
    }

    size = strlen(value) + 1;
    if (param_value_size_ret != NULL) {
        *param_value_size_ret = size;
    }
    if (param_value != NULL) {
        if (param_value_size < size) {
            return CL_INVALID_VALUE;
        }
        memcpy(param_value, value, size);
    }
    return CL_SUCCESS;
}

CL_API_ENTRY void *CL_API_CALL
clGetExtensionFunctionAddress(const char *func_name)
{
    if (func_name == NULL) {
        return NULL;
    }
    if (strcmp(func_name, "clIcdGetPlatformIDsKHR") == 0) {
        return (void *)dummy_get_platform_ids;
    }
    if (strcmp(func_name, "clGetPlatformInfo") == 0) {
        return (void *)clGetPlatformInfo;
    }
    return NULL;
}
