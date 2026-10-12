/* Native HarmonyOS ARM64 application-storage MOD decoding regression. */
#define _POSIX_C_SOURCE 200809L
#include <dumb.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/utsname.h>
#include <unistd.h>

#define CHECK(x) do { if (!(x)) { fprintf(stderr, "FAIL line %d: %s\n", __LINE__, #x); goto cleanup; } } while (0)

int main(void)
{
    struct utsname host;
    const char *root = getenv("TMPDIR");
    char directory[4096] = {0}, filename[4096] = {0};
    unsigned char mod[1084 + 1024 + 64] = {0};
    short pcm[4096 * 2];
    FILE *file = NULL;
    DUH *duh = NULL;
    DUH_SIGRENDERER *renderer = NULL;
    int result = 1, created = 0, nonzero = 0, length;
    long frames, i;

    dumb_register_stdfiles();
    CHECK(uname(&host) == 0);
    CHECK(strcmp(host.sysname, "HarmonyOS") == 0);
    CHECK(strcmp(host.machine, "aarch64") == 0 && sizeof(void *) == 8);
    if (!root || !*root) root = getenv("HOME");
    CHECK(root != NULL);
    CHECK(strncmp(root, "/storage/", 9) == 0 || strncmp(root, "/data/storage/", 14) == 0);
    length = snprintf(directory, sizeof(directory), "%s/libdumb-ohos-XXXXXX", root);
    CHECK(length > 0 && (size_t)length < sizeof(directory));
    CHECK(mkdtemp(directory) != NULL);
    created = 1;
    length = snprintf(filename, sizeof(filename), "%s/鸿蒙音乐.mod", directory);
    CHECK(length > 0 && (size_t)length < sizeof(filename));

    memcpy(mod, "Harmony storage", 15);
    mod[43] = 32; mod[45] = 64; mod[49] = 32;
    mod[950] = 1;
    memcpy(mod + 1080, "M.K.", 4);
    mod[1084] = 1; mod[1085] = 0xac; mod[1086] = 0x10;
    for (i = 0; i < 64; ++i) mod[2108 + i] = i < 32 ? 80 : (unsigned char)-80;
    file = fopen(filename, "wb");
    CHECK(file != NULL);
    CHECK(fwrite(mod, 1, sizeof(mod), file) == sizeof(mod));
    result = fclose(file);
    file = NULL;
    CHECK(result == 0);
    result = 1;

    /* Exercise the library's actual filesystem reader, not memory I/O. */
    duh = dumb_load_mod(filename);
    CHECK(duh != NULL && duh_get_length(duh) > 0);
    renderer = duh_start_sigrenderer(duh, 0, 2, 0);
    CHECK(renderer != NULL);
    CHECK(duh_sigrenderer_get_n_channels(renderer) == 2);
    memset(pcm, 0, sizeof(pcm));
    frames = duh_render(renderer, 16, 0, 1.0f, 65536.0f / 44100.0f, 4096, pcm);
    CHECK(frames == 4096);
    for (i = 0; i < frames * 2; ++i) if (pcm[i] != 0) nonzero = 1;
    CHECK(nonzero && duh_sigrenderer_get_position(renderer) > 0);
    result = 0;

cleanup:
    if (file) fclose(file);
    if (renderer) duh_end_sigrenderer(renderer);
    if (duh) unload_duh(duh);
    if (created) {
        if (*filename && unlink(filename) != 0 && access(filename, F_OK) == 0) result = 1;
        if (rmdir(directory) != 0) result = 1;
    }
    dumb_exit();
    if (result == 0) puts("PASS ohos_arm64_storage_mod_decode");
    return result;
}
