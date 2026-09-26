#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <dlfcn.h>

/* Minimal libretro ABI surface used by the consumer test. The public API of a
 * libretro core is the retro_* ABI defined in libretro.h; a frontend loads the
 * core .so by exact filename and calls these symbols via dlsym. */
struct retro_system_info {
    const char *library_name;
    const char *library_version;
    const char *valid_extensions;
    unsigned need_fullpath;
    unsigned block_extract;
};

typedef unsigned (*retro_api_version_fn)(void);
typedef void (*retro_get_system_info_fn)(struct retro_system_info *info);

int main(int argc, char **argv) {
    const char *core_path;
    void *handle;
    retro_api_version_fn api_version;
    retro_get_system_info_fn get_info;
    struct retro_system_info info;

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
    get_info = (retro_get_system_info_fn)dlsym(handle, "retro_get_system_info");
    if (!api_version || !get_info) {
        fprintf(stderr, "dlsym failed: %s\n", dlerror());
        dlclose(handle);
        return 1;
    }

    if (api_version() != 1) {
        fprintf(stderr, "retro_api_version() = %u, expected 1\n", api_version());
        dlclose(handle);
        return 1;
    }

    memset(&info, 0, sizeof(info));
    get_info(&info);
    if (!info.library_name || strcmp(info.library_name, "Beetle VB") != 0) {
        fprintf(stderr, "library_name = %s, expected 'Beetle VB'\n",
                info.library_name ? info.library_name : "(null)");
        dlclose(handle);
        return 1;
    }

    printf("consumer ok: library_name=%s library_version=%s valid_extensions=%s "
           "retro_api_version=%u\n",
           info.library_name, info.library_version ? info.library_version : "(null)",
           info.valid_extensions ? info.valid_extensions : "(null)", api_version());
    dlclose(handle);
    return 0;
}
