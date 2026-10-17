// openxr 1.1.63 (OHOS) 消费者验证程序。
//
// 参数：argv[1] = 运行时清单 JSON 路径；argv[2] = stub 哨兵文件路径；
//       argv[3] = 一个空目录，用来当 XDG_CONFIG_HOME/XDG_CONFIG_DIRS。
//
// 三个场景（任一失败即非零退出）：
//
//   A. 无运行时可发现 —— XR_RUNTIME_JSON 未设、XDG 全指向空目录时，
//      xrCreateInstance 必须返回 XR_ERROR_RUNTIME_UNAVAILABLE。
//      这条能成立的前提是 manifest_file.cpp 的 XDG 分支（XR_OS_LINUX）
//      真的被编译出来了，即补丁 0002 生效。若补丁没生效，HarmonyOS 会
//      走到 PlatformGetGlobalRuntimeFileName 那条平台回退分支，行为不同。
//
//   B. loader 内核符号在 —— xrGetInstanceProcAddr(XR_NULL_HANDLE,
//      "xrCreateInstance", &fp) 返回 XR_SUCCESS 且 fp 非空。这是 loader
//      的 version script（openxr-loader.map）没把符号裁掉的直接证据。
//
//   C. loader 能在 OHOS 上 dlopen 一个运行时 —— XR_RUNTIME_JSON 指向
//      合法的运行时清单后，stub 必须真的被 dlopen + dlsym + 调用。
//      判据是哨兵文件出现，而不是 xrCreateInstance 的返回码：
//      LoadRuntime 会把 negotiate 的任何失败统一归一化成
//      XR_ERROR_RUNTIME_UNAVAILABLE，与"根本没找到运行时"同码，
//      退出码分不出来。
#include <openxr/openxr.h>

#include <cstdio>
#include <cstdlib>
#include <cstring>

namespace {

int failures = 0;

void Check(bool ok, const char* what) {
    if (ok) {
        std::printf("ok   - %s\n", what);
    } else {
        std::printf("FAIL - %s\n", what);
        ++failures;
    }
}

bool FileExists(const char* path) {
    std::FILE* handle = std::fopen(path, "r");
    if (handle == nullptr) {
        return false;
    }
    std::fclose(handle);
    return true;
}

void SetEnv(const char* key, const char* value) {
#if defined(_WIN32)
    _putenv_s(key, value);
#else
    setenv(key, value, 1);
#endif
}

void UnsetEnv(const char* key) {
#if defined(_WIN32)
    _putenv_s(key, "");
#else
    unsetenv(key);
#endif
}

}  // namespace

int main(int argc, char** argv) {
    if (argc < 4) {
        std::fprintf(stderr,
                     "usage: %s <runtime_json> <marker> <empty_xdg_dir>\n",
                     argv[0]);
        return 2;
    }
    const char* runtime_json = argv[1];
    const char* marker = argv[2];
    const char* empty_xdg = argv[3];

    std::remove(marker);

    // ---------------------------------------------------------------- B
    // loader 内核符号必须经 version script 导出（场景 B 与运行时无关）
    PFN_xrVoidFunction fp = nullptr;
    XrResult result =
        xrGetInstanceProcAddr(XR_NULL_HANDLE, "xrCreateInstance", &fp);
    Check(result == XR_SUCCESS, "xrGetInstanceProcAddr(xrCreateInstance) == SUCCESS");
    Check(fp != nullptr, "xrCreateInstance 函数指针非空");

    // 未知名查找必须被拒（反证不是"任何字符串都返回 SUCCESS"）。
    // 期望码是 XR_ERROR_HANDLE_INVALID 而不是 XR_ERROR_FUNCTION_UNSUPPORTED：
    // null instance 下 loader 只放行 4 个函数（xrGetInstanceProcAddr /
    // xrInitializeLoaderKHR / xrEnumerateApiLayerProperties /
    // xrEnumerateInstanceExtensionProperties / xrCreateInstance），其余一律在
    // loader_core.cpp 的 "it is invalid to pass XR_NULL_HANDLE" 分支被拦下。
    PFN_xrVoidFunction unknown = reinterpret_cast<PFN_xrVoidFunction>(0x1);
    result = xrGetInstanceProcAddr(XR_NULL_HANDLE, "xrNotARealFunction", &unknown);
    Check(result == XR_ERROR_HANDLE_INVALID,
          "null instance + 未知名返回 XR_ERROR_HANDLE_INVALID");
    Check(unknown == nullptr, "查找失败时函数指针被清空");

    // ---------------------------------------------------------------- A
    // 无运行时：XR_RUNTIME_JSON 不设，XDG 全部指向空目录
    UnsetEnv("XR_RUNTIME_JSON");
    SetEnv("XDG_CONFIG_HOME", empty_xdg);
    SetEnv("XDG_CONFIG_DIRS", empty_xdg);
    std::remove(marker);

    XrInstance instance = XR_NULL_HANDLE;
    XrInstanceCreateInfo create_info{XR_TYPE_INSTANCE_CREATE_INFO};
    std::strncpy(create_info.applicationInfo.applicationName, "openxr-conan-test",
                 XR_MAX_APPLICATION_NAME_SIZE - 1);
    create_info.applicationInfo.applicationVersion = 1;
    std::strncpy(create_info.applicationInfo.engineName, "none",
                 XR_MAX_ENGINE_NAME_SIZE - 1);
    create_info.applicationInfo.engineVersion = 0;
    create_info.applicationInfo.apiVersion = XR_CURRENT_API_VERSION;

    result = xrCreateInstance(&create_info, &instance);
    Check(result == XR_ERROR_RUNTIME_UNAVAILABLE,
          "无运行时时 xrCreateInstance == XR_ERROR_RUNTIME_UNAVAILABLE");
    Check(!FileExists(marker), "无运行时时 stub 未被 dlopen（哨兵文件不存在）");

    // ---------------------------------------------------------------- C
    // 有运行时：XR_RUNTIME_JSON 指向合法清单，stub 必须真被调进来
    SetEnv("XR_RUNTIME_JSON", runtime_json);
    SetEnv("OPENXR_STUB_MARKER", marker);

    instance = XR_NULL_HANDLE;
    result = xrCreateInstance(&create_info, &instance);
    // 返回码无法区分"没找到"与"negotiate 失败"（LoadRuntime 把后者归一化
    // 成同一个码），所以这里只断言它没崩，真正的判据是下面的哨兵文件。
    Check(result == XR_ERROR_RUNTIME_UNAVAILABLE,
          "stub negotiate 失败被归一化为 XR_ERROR_RUNTIME_UNAVAILABLE");
    Check(FileExists(marker),
          "stub 真的被 dlopen+dlsym+调用（哨兵文件出现）");

    if (failures != 0) {
        std::fprintf(stderr, "%d assertion(s) failed\n", failures);
        return 1;
    }
    std::printf("all checks passed\n");
    return 0;
}
