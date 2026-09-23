// 最小 XR 运行时：只实现 loader 会调的第一个入口
// xrNegotiateLoaderRuntimeInterface。
//
// 之所以故意让它"谈判失败"，是因为 test_package 要断言的不是"运行时可用"，
// 而是"OHOS 上 loader 能不能把这个 .so dlopen 起来并调进来"。判据是哨兵文件：
// 函数被调用就写一个文件，文件出现即证明 dlopen + dlsym + 调用链全通。
//
// 不能靠 xrCreateInstance 的返回码来判断：loader 的
// RuntimeInterface::LoadRuntime 末尾会把 negotiate 的任何失败统一归一化成
// XR_ERROR_RUNTIME_UNAVAILABLE，与"根本没找到运行时"完全同一个码。
#include <openxr/openxr_loader_negotiation.h>

#include <cstdio>
#include <cstdlib>

#if defined(_WIN32)
#define STUB_EXPORT __declspec(dllexport)
#else
#define STUB_EXPORT __attribute__((visibility("default")))
#endif

extern "C" {

STUB_EXPORT XrResult XRAPI_CALL
xrNegotiateLoaderRuntimeInterface(const XrNegotiateLoaderInfo* loaderInfo,
                                  XrNegotiateRuntimeRequest* runtimeRequest) {
    // 哨兵：证明本函数真的被 loader 调用了（而不是清单被静默丢弃）
    const char* marker = std::getenv("OPENXR_STUB_MARKER");
    if (marker != nullptr && marker[0] != '\0') {
        std::FILE* handle = std::fopen(marker, "w");
        if (handle != nullptr) {
            std::fputs("negotiated\n", handle);
            std::fclose(handle);
        }
    }

    if (loaderInfo == nullptr || runtimeRequest == nullptr) {
        return XR_ERROR_INITIALIZATION_FAILED;
    }
    return XR_ERROR_INITIALIZATION_FAILED;
}

}  // extern "C"
