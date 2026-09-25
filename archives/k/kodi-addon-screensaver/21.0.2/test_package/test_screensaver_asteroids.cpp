// Consumer-side verification for kodi-addon-screensaver/21.0.2.
//
// A Kodi screensaver add-on is a module loaded by the Kodi host; it has no
// standalone entry point and needs a display to render. What CAN be verified
// headlessly, against the packaged artifact itself, is the Kodi 21 binary
// add-on contract:
//   - the module loads (dlopen) and exports the three C entry points every
//     Kodi 21 binary add-on defines through kodi/AddonBase.h:
//     ADDON_Create, ADDON_GetTypeVersion, ADDON_GetTypeMinVersion;
//   - ADDON_GetTypeVersion()/ADDON_GetTypeMinVersion() report the screensaver
//     instance API version recorded in kodi/versions.h of the xbmc 21.3-Omega
//     SDK: ADDON_INSTANCE_SCREENSAVER = 108,
//     ADDON_INSTANCE_VERSION_SCREENSAVER = "2.2.0".

#include <dlfcn.h>

#include <cstdio>
#include <cstring>

int main(int argc, char** argv) {
    if (argc != 2) {
        std::fprintf(stderr, "usage: %s <path to screensaver.asteroids.so>\n", argv[0]);
        return 2;
    }
    const char* module_path = argv[1];

    void* handle = dlopen(module_path, RTLD_LAZY | RTLD_LOCAL);
    if (handle == nullptr) {
        std::fprintf(stderr, "FAIL: dlopen(%s): %s\n", module_path, dlerror());
        return 1;
    }

    const char* required_symbols[] = {
        "ADDON_Create",
        "ADDON_GetTypeVersion",
        "ADDON_GetTypeMinVersion",
    };
    for (const char* symbol : required_symbols) {
        void* entry = dlsym(handle, symbol);
        if (entry == nullptr) {
            std::fprintf(stderr, "FAIL: missing add-on entry point %s\n", symbol);
            dlclose(handle);
            return 1;
        }
    }

    using GetTypeVersionFn = const char* (*)(int);
    GetTypeVersionFn get_type_version = reinterpret_cast<GetTypeVersionFn>(
        dlsym(handle, "ADDON_GetTypeVersion"));
    GetTypeVersionFn get_type_min_version = reinterpret_cast<GetTypeVersionFn>(
        dlsym(handle, "ADDON_GetTypeMinVersion"));

    constexpr int kAddonInstanceScreensaver = 108;
    const char* version = get_type_version(kAddonInstanceScreensaver);
    if (version == nullptr || std::strcmp(version, "2.2.0") != 0) {
        std::fprintf(stderr, "FAIL: screensaver instance version is %s, expected 2.2.0\n",
                     version == nullptr ? "<null>" : version);
        dlclose(handle);
        return 1;
    }
    const char* min_version = get_type_min_version(kAddonInstanceScreensaver);
    if (min_version == nullptr || std::strcmp(min_version, "2.2.0") != 0) {
        std::fprintf(stderr, "FAIL: screensaver instance min version is %s, expected 2.2.0\n",
                     min_version == nullptr ? "<null>" : min_version);
        dlclose(handle);
        return 1;
    }

    dlclose(handle);
    std::printf("PASS: %s exports the Kodi binary add-on entry points and reports "
                "screensaver instance API 2.2.0\n",
                module_path);
    return 0;
}
