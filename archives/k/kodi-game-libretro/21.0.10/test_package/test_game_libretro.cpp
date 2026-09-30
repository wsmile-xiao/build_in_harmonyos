// Consumer-side verification for kodi-game-libretro/21.0.10.
//
// A Kodi game client add-on is a module loaded by the Kodi host; it has no
// standalone entry point and drives gameplay through the Kodi Game API. What
// CAN be verified headlessly, against the packaged artifact itself, is the
// Kodi 21 binary add-on contract:
//   - the module loads (dlopen) and exports the three C entry points every
//     Kodi 21 binary add-on defines through kodi/AddonBase.h:
//     ADDON_Create, ADDON_GetTypeVersion, ADDON_GetTypeMinVersion;
//   - ADDON_GetTypeVersion()/ADDON_GetTypeMinVersion() report the game
//     client instance API version recorded in kodi/versions.h of the
//     xbmc 21.3-Omega SDK: ADDON_INSTANCE_GAME = 104,
//     ADDON_INSTANCE_VERSION_GAME = "3.0.2" (min "3.0.0").

#include <dlfcn.h>

#include <cstdio>
#include <cstring>

int main(int argc, char** argv) {
    if (argc != 2) {
        std::fprintf(stderr, "usage: %s <path to game.libretro.so>\n", argv[0]);
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

    constexpr int kAddonInstanceGame = 104;
    const char* version = get_type_version(kAddonInstanceGame);
    if (version == nullptr || std::strcmp(version, "3.0.2") != 0) {
        std::fprintf(stderr, "FAIL: game instance version is %s, expected 3.0.2\n",
                     version == nullptr ? "<null>" : version);
        dlclose(handle);
        return 1;
    }
    const char* min_version = get_type_min_version(kAddonInstanceGame);
    if (min_version == nullptr || std::strcmp(min_version, "3.0.0") != 0) {
        std::fprintf(stderr, "FAIL: game instance min version is %s, expected 3.0.0\n",
                     min_version == nullptr ? "<null>" : min_version);
        dlclose(handle);
        return 1;
    }

    dlclose(handle);
    std::printf("PASS: %s exports the Kodi binary add-on entry points and reports "
                "game client instance API 3.0.2 (min 3.0.0)\n",
                module_path);
    return 0;
}
