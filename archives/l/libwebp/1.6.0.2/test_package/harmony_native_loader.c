/* Signed native loader: no DT_NEEDED link to WebP, real dlopen and codec oracle. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <limits.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/utsname.h>

static int within(const char *path, const char *root) {
  const size_t n = strlen(root);
  return strncmp(path, root, n) == 0 && path[n] == '/';
}
static int fail(const char *stage) {
  fprintf(stderr, "HARMONY_NATIVE_LOADER_FAIL=%s\n", stage);
  return 1;
}
int main(int argc, char **argv) {
  char package[PATH_MAX], lib[PATH_MAX], sharp[PATH_MAX], requested[PATH_MAX];
  struct utsname platform;
  if (argc != 3 || uname(&platform) || strcmp(platform.sysname, "HarmonyOS") ||
      strcmp(platform.machine, "aarch64")) return fail("platform_or_arguments");
  if (!realpath(argv[1], package) || !realpath(argv[2], lib) ||
      !within(lib, package) || strchr(lib, '"') || strchr(lib, '\\') ||
      strchr(lib, '\n')) return fail("canonical_package_library");
  if (snprintf(requested, sizeof requested, "%s/lib/libsharpyuv.so", package)
      >= (int)sizeof requested || !realpath(requested, sharp) ||
      !within(sharp, package)) return fail("private_sharpyuv_provider");
  /* Absolute preload is a genuine provider, not a system-library substitution. */
  void *yuv = dlopen(sharp, RTLD_NOW | RTLD_LOCAL);
  if (!yuv) { fprintf(stderr, "%s\n", dlerror()); return fail("sharpyuv_dlopen"); }
  void *codec = dlopen(lib, RTLD_NOW | RTLD_LOCAL);
  if (!codec) { fprintf(stderr, "%s\n", dlerror()); dlclose(yuv); return fail("webp_dlopen"); }
  size_t (*encode)(const uint8_t *, int, int, int, uint8_t **) =
      (size_t (*)(const uint8_t *, int, int, int, uint8_t **))dlsym(codec, "WebPEncodeLosslessRGBA");
  uint8_t *(*decode)(const uint8_t *, size_t, int *, int *) =
      (uint8_t *(*)(const uint8_t *, size_t, int *, int *))dlsym(codec, "WebPDecodeRGBA");
  void (*release)(void *) = (void (*)(void *))dlsym(codec, "WebPFree");
  if (!encode || !decode || !release) return fail("codec_symbol_binding");
  Dl_info identity;
  char mapped_symbol[PATH_MAX];
  if (!dladdr((void *)encode, &identity) || !identity.dli_fname ||
      !realpath(identity.dli_fname, mapped_symbol) || strcmp(mapped_symbol, lib))
    return fail("foreign_codec_symbol");
  const uint8_t rgba[4] = {31, 63, 127, 255};
  uint8_t *encoded = NULL;
  const size_t size = encode(rgba, 1, 1, 4, &encoded);
  if (!size || !encoded) return fail("actual_lossless_encode");
  int width = 0, height = 0;
  uint8_t *decoded = decode(encoded, size, &width, &height);
  const int exact = decoded && width == 1 && height == 1 && !memcmp(decoded, rgba, 4);
  release(decoded); release(encoded);
  if (!exact) return fail("actual_rgba_roundtrip");
  FILE *maps = fopen("/proc/self/maps", "r");
  if (!maps) return fail("actual_process_maps");
  char line[8192], canonical[PATH_MAX];
  int webp_seen = 0, sharp_seen = 0, foreign = 0;
  while (fgets(line, sizeof line, maps)) {
    char *path = strchr(line, '/');
    if (!path) continue;
    path[strcspn(path, "\n")] = 0;
    const int webp = strstr(path, "/libwebp.so") != NULL;
    const int sharpyuv = strstr(path, "/libsharpyuv.so") != NULL;
    if (!webp && !sharpyuv) continue;
    if (!realpath(path, canonical) || !within(canonical, package)) { foreign = 1; break; }
    if (webp) { if (strcmp(canonical, lib)) { foreign = 1; break; } webp_seen = 1; }
    if (sharpyuv) { if (strcmp(canonical, sharp)) { foreign = 1; break; } sharp_seen = 1; }
  }
  const int maps_error = ferror(maps); fclose(maps);
  if (maps_error || foreign || !webp_seen || !sharp_seen) return fail("foreign_or_ambiguous_mapping");
  printf("{\"actual_loader_and_codec_rc\":0,\"library\":\"%s\","
         "\"webp_mapping\":[\"%s\"],\"sharpyuv_mapping\":[\"%s\"],"
         "\"native_loader\":true,\"width\":1,\"height\":1}\n", lib, lib, sharp);
  if (dlclose(codec) || dlclose(yuv)) return fail("loader_cleanup");
  return 0;
}
