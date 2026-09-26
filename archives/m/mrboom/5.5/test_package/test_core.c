/*
 * Consumer test for the mrboom libretro core.
 *
 * A libretro core is a plugin: frontends load it with dlopen() and drive it
 * through the mandatory C ABI (retro_* symbols exported via link.T).
 * This test loads the packaged core exactly like a frontend would and
 * asserts real behavior of the mandatory API entry points:
 *   - ABI version contract (retro_api_version == RETRO_API_VERSION)
 *   - static core metadata (retro_get_system_info)
 *   - a minimal frontend lifecycle with an environment stub
 *     (retro_set_environment -> retro_init -> retro_deinit)
 */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <stdbool.h>

typedef void (*retro_set_environment_t)(bool (*)(unsigned, void *));
typedef void (*retro_init_t)(void);
typedef void (*retro_deinit_t)(void);
typedef unsigned (*retro_api_version_t)(void);
typedef void (*retro_get_system_info_t)(struct retro_system_info *);

struct retro_system_info {
    const char *library_name;
    const char *library_version;
    const char *valid_extensions;
    bool need_fullpath;
    bool block_extract;
};

static int failures = 0;

#define CHECK(cond, msg)                                     \
    do {                                                     \
        if (cond) {                                          \
            printf("PASS: %s\n", msg);                       \
        } else {                                             \
            printf("FAIL: %s\n", msg);                       \
            failures++;                                      \
        }                                                    \
    } while (0)

/* Environment stub: answer "not supported" to every frontend query,
 * exactly what a bare-bones frontend does. Keeps the core on its
 * fallback paths (fallback log, /tmp base directory). */
static bool env_stub(unsigned cmd, void *data)
{
    (void)cmd;
    (void)data;
    return false;
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        printf("usage: %s <path-to-mrboom_libretro.so>\n", argv[0]);
        return 2;
    }

    void *handle = dlopen(argv[1], RTLD_NOW | RTLD_LOCAL);
    if (!handle) {
        printf("FAIL: dlopen(%s): %s\n", argv[1], dlerror());
        return 1;
    }
    printf("PASS: core loaded (%s)\n", argv[1]);

    retro_api_version_t api_version =
        (retro_api_version_t)dlsym(handle, "retro_api_version");
    CHECK(api_version != NULL, "retro_api_version exported");
    if (api_version) {
        unsigned v = api_version();
        printf("retro_api_version() = %u\n", v);
        CHECK(v == 1u, "retro_api_version() == RETRO_API_VERSION (1)");
    }

    retro_get_system_info_t get_system_info =
        (retro_get_system_info_t)dlsym(handle, "retro_get_system_info");
    CHECK(get_system_info != NULL, "retro_get_system_info exported");
    if (get_system_info) {
        struct retro_system_info info;
        memset(&info, 0, sizeof(info));
        get_system_info(&info);
        printf("library_name=\"%s\" version=\"%s\"\n",
               info.library_name ? info.library_name : "(null)",
               info.library_version ? info.library_version : "(null)");
        CHECK(info.library_name && strcmp(info.library_name, "Mr.Boom") == 0,
              "library_name == \"Mr.Boom\"");
        CHECK(info.library_version && info.library_version[0] != '\0',
              "library_version non-empty");
        CHECK(info.valid_extensions == NULL && !info.need_fullpath,
              "static metadata: extensions=NULL, need_fullpath=false");
    }

    retro_set_environment_t set_env =
        (retro_set_environment_t)dlsym(handle, "retro_set_environment");
    retro_init_t init = (retro_init_t)dlsym(handle, "retro_init");
    retro_deinit_t deinit = (retro_deinit_t)dlsym(handle, "retro_deinit");
    CHECK(set_env && init && deinit,
          "retro_set_environment/retro_init/retro_deinit exported");

    if (set_env && init && deinit) {
        set_env(env_stub);
        init();
        printf("PASS: retro_init() lifecycle with env stub\n");
        deinit();
        printf("PASS: retro_deinit() clean\n");
    }

    dlclose(handle);

    if (failures) {
        printf("FAILED: %d check(s)\n", failures);
        return 1;
    }
    printf("ALL CHECKS PASSED\n");
    return 0;
}
