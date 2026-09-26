#include <stdbool.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>

/* HarmonyOS-specific test for the beetle-vb-libretro core.
 *
 * Unlike the consumer smoke test (test.c, which validates the public ABI
 * surface), this test exercises the full frontend lifecycle on the OHOS
 * runtime: retro_init() → retro_get_system_av_info() (timing/geometry) →
 * retro_get_system_info() (extensions) → retro_deinit(). It verifies the
 * core can be loaded, initialized and torn down on the aarch64 OHOS
 * runtime and that the emulator parameters it reports are the expected
 * Virtual Boy constants. */

struct retro_system_info {
    const char *library_name;
    const char *library_version;
    const char *valid_extensions;
    unsigned need_fullpath;
    unsigned block_extract;
};

struct retro_game_geometry {
    unsigned base_width;
    unsigned base_height;
    unsigned max_width;
    unsigned max_height;
    float aspect_ratio;
};

struct retro_system_timing {
    double fps;
    double sample_rate;
};

struct retro_system_av_info {
    struct retro_game_geometry geometry;
    struct retro_system_timing timing;
};

typedef unsigned (*retro_api_version_fn)(void);
typedef void (*retro_init_fn)(void);
typedef void (*retro_deinit_fn)(void);
typedef void (*retro_get_system_info_fn)(struct retro_system_info *info);
typedef void (*retro_get_system_av_info_fn)(struct retro_system_av_info *info);
typedef bool (*retro_environment_fn)(unsigned cmd, void *data);
typedef void (*retro_set_environment_fn)(retro_environment_fn callback);

/* Minimal frontend environment callback (libretro ABI contract: must be
 * registered via retro_set_environment() before retro_init()). A real
 * frontend (RetroArch) implements the full interface; here we accept the
 * informational SET_* commands and decline GET_* (no variables/logging/perf
 * interfaces in the test harness), which is the documented default
 * behaviour for a minimal frontend. */
static bool test_ohos_environ(unsigned cmd, void *data) {
    (void)data;
    switch (cmd) {
        case 8:   /* RETRO_ENVIRONMENT_SET_PERFORMANCE_LEVEL */
        case 10:  /* RETRO_ENVIRONMENT_SET_PIXEL_FORMAT */
        case 16:  /* RETRO_ENVIRONMENT_SET_VARIABLES */
            return true;
        default:
            return false;
    }
}

int main(int argc, char **argv) {
    const char *core_path;
    void *handle;
    retro_api_version_fn api_version;
    retro_init_fn core_init;
    retro_deinit_fn core_deinit;
    retro_get_system_info_fn get_info;
    retro_get_system_av_info_fn get_av_info;
    retro_set_environment_fn set_environment;
    struct retro_system_info info;
    struct retro_system_av_info av;

    if (argc < 2) {
        fprintf(stderr, "usage: %s <path-to-mednafen_vb_libretro.so>\n", argv[0]);
        return 2;
    }
    core_path = argv[1];

    handle = dlopen(core_path, RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        fprintf(stderr, "dlopen(%s) failed: %s\n", core_path, dlerror());
        return 1;
    }

    api_version = (retro_api_version_fn)dlsym(handle, "retro_api_version");
    core_init = (retro_init_fn)dlsym(handle, "retro_init");
    core_deinit = (retro_deinit_fn)dlsym(handle, "retro_deinit");
    get_info = (retro_get_system_info_fn)dlsym(handle, "retro_get_system_info");
    get_av_info = (retro_get_system_av_info_fn)dlsym(handle, "retro_get_system_av_info");
    set_environment = (retro_set_environment_fn)dlsym(handle, "retro_set_environment");
    if (!api_version || !core_init || !core_deinit || !get_info || !get_av_info || !set_environment) {
        fprintf(stderr, "dlsym failed: %s\n", dlerror());
        dlclose(handle);
        return 1;
    }

    if (api_version() != 1) {
        fprintf(stderr, "retro_api_version() = %u, expected 1\n", api_version());
        dlclose(handle);
        return 1;
    }

    /* Full frontend lifecycle on the OHOS runtime: the libretro ABI
     * contract requires the environment callback before retro_init(). */
    set_environment(test_ohos_environ);
    core_init();

    memset(&info, 0, sizeof(info));
    get_info(&info);
    if (!info.library_name || strcmp(info.library_name, "Beetle VB") != 0) {
        fprintf(stderr, "library_name = %s, expected 'Beetle VB'\n",
                info.library_name ? info.library_name : "(null)");
        core_deinit();
        dlclose(handle);
        return 1;
    }
    if (!info.valid_extensions || strstr(info.valid_extensions, "vb") == NULL) {
        fprintf(stderr, "valid_extensions = %s, expected to include 'vb'\n",
                info.valid_extensions ? info.valid_extensions : "(null)");
        core_deinit();
        dlclose(handle);
        return 1;
    }

    memset(&av, 0, sizeof(av));
    get_av_info(&av);
    if (av.timing.fps <= 0.0 || av.timing.sample_rate <= 0.0) {
        fprintf(stderr, "unexpected timing: fps=%.2f sample_rate=%.2f\n",
                av.timing.fps, av.timing.sample_rate);
        core_deinit();
        dlclose(handle);
        return 1;
    }
    if (av.geometry.base_width == 0 || av.geometry.base_height == 0) {
        fprintf(stderr, "unexpected geometry: %ux%u\n",
                av.geometry.base_width, av.geometry.base_height);
        core_deinit();
        dlclose(handle);
        return 1;
    }

    core_deinit();
    printf("ohos lifecycle ok: fps=%.2f sample_rate=%.2f geometry=%ux%u "
           "extensions=%s\n",
           av.timing.fps, av.timing.sample_rate,
           av.geometry.base_width, av.geometry.base_height,
           info.valid_extensions);
    dlclose(handle);
    return 0;
}
