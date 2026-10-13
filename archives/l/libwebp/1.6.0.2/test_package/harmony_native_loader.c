/* Signed native loader: no DT_NEEDED link to WebP, real dlopen and codec oracle. */
#define _GNU_SOURCE
#include <dlfcn.h>
#include <errno.h>
#include <limits.h>
#include <link.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/utsname.h>
#include <unistd.h>

static int within(const char *path, const char *root) {
  const size_t n = strlen(root);
  return strncmp(path, root, n) == 0 && path[n] == '/';
}
static int fail(const char *stage) {
  fprintf(stderr, "HARMONY_NATIVE_LOADER_FAIL=%s\n", stage);
  return 1;
}
struct load_segment { uintptr_t begin, end; unsigned long offset; };
struct loaded_object {
  const char *expected;
  struct load_segment segments[32];
  size_t count;
  int objects, rejected;
};
static int collect_object(struct dl_phdr_info *info, size_t size, void *data) {
  struct loaded_object *object = data;
  char canonical[PATH_MAX];
  (void)size;
  if (!info->dlpi_name || !*info->dlpi_name) return 0;
  const char *name = strrchr(info->dlpi_name, '/');
  const char *wanted = strrchr(object->expected, '/');
  name = name ? name + 1 : info->dlpi_name;
  wanted = wanted ? wanted + 1 : object->expected;
  const char *stem = strstr(wanted, "libsharpyuv.so") ? "libsharpyuv.so" : "libwebp.so";
  if (strncmp(name, stem, strlen(stem))) return 0;
  if (!realpath(info->dlpi_name, canonical) || strcmp(canonical, object->expected)) {
    object->rejected = 1; return 0;
  }
  ++object->objects;
  const long page_long = sysconf(_SC_PAGESIZE);
  if (page_long <= 0 || ((uintptr_t)page_long & ((uintptr_t)page_long - 1))) {
    object->rejected = 1; return 0;
  }
  const uintptr_t page = (uintptr_t)page_long;
  for (size_t i = 0; i < info->dlpi_phnum; ++i) {
    const ElfW(Phdr) *p = &info->dlpi_phdr[i];
    if (p->p_type != PT_LOAD || !p->p_filesz) continue;
    if (object->count == 32 || p->p_vaddr > UINTPTR_MAX - info->dlpi_addr) {
      object->rejected = 1; return 0;
    }
    uintptr_t start = info->dlpi_addr + p->p_vaddr;
    if (p->p_filesz > UINTPTR_MAX - start ||
        start + p->p_filesz > UINTPTR_MAX - (page - 1)) {
      object->rejected = 1; return 0;
    }
    struct load_segment *segment = &object->segments[object->count++];
    segment->begin = start & ~(page - 1);
    segment->end = (start + p->p_filesz + page - 1) & ~(page - 1);
    segment->offset = p->p_offset & ~(page - 1);
  }
  return 0;
}
static int owns_mapping(const struct loaded_object *object,
                        uintptr_t begin, uintptr_t end, unsigned long offset) {
  if (object->rejected || object->objects != 1 || begin >= end) return 0;
  for (size_t i = 0; i < object->count; ++i) {
    const struct load_segment *s = &object->segments[i];
    if (begin >= s->begin && end <= s->end &&
        begin - s->begin <= ULONG_MAX - s->offset &&
        offset == s->offset + (begin - s->begin)) return 1;
  }
  return 0;
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
  struct loaded_object webp_object = {.expected = lib};
  struct loaded_object sharp_object = {.expected = sharp};
  dl_iterate_phdr(collect_object, &webp_object);
  dl_iterate_phdr(collect_object, &sharp_object);
  if (webp_object.rejected || sharp_object.rejected ||
      webp_object.objects != 1 || sharp_object.objects != 1 ||
      !webp_object.count || !sharp_object.count) return fail("foreign_loader_object");
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
    unsigned long begin, end, offset, inode;
    unsigned int major, minor;
    char permissions[5];
    const struct loaded_object *object = webp ? &webp_object : &sharp_object;
    if (sscanf(line, "%lx-%lx %4s %lx %x:%x %lu", &begin, &end,
               permissions, &offset, &major, &minor, &inode) != 7 || !inode ||
        !owns_mapping(object, begin, end, offset)) {
      fprintf(stderr, "HARMONY_MAPPING_REJECT=loader_segment_or_offset; path=%s\n", path);
      foreign = 1; break;
    }
    if (!realpath(path, canonical)) {
      const int saved_errno = errno;
      /* HMDFS exposes a kernel backing path that may not be in this process's
         VFS view. Do not translate path prefixes or accept basenames alone:
         the actual canonical loader object, PT_LOAD address and file offset
         above must independently agree. Only an absent path is admissible. */
      if (saved_errno != ENOENT) {
        fprintf(stderr, "HARMONY_MAPPING_REJECT=realpath; errno=%d; path=%s\n", saved_errno, path);
        foreign = 1; break;
      }
      if (strlen(object->expected) >= sizeof canonical) return fail("loader_path_length");
      strcpy(canonical, object->expected);
      fprintf(stderr, "HARMONY_MAPPING_LOADER_WITNESS=PT_LOAD_address_and_offset; backing_path=%s; canonical=%s\n", path, canonical);
    }
    if (!within(canonical, package)) {
      fprintf(stderr, "HARMONY_MAPPING_REJECT=outside_package; path=%s; canonical=%s; package=%s\n", path, canonical, package);
      foreign = 1; break;
    }
    if (webp) {
      if (strcmp(canonical, lib)) {
        fprintf(stderr, "HARMONY_MAPPING_REJECT=webp_identity; path=%s; canonical=%s; expected=%s\n", path, canonical, lib);
        foreign = 1; break;
      }
      webp_seen = 1;
    }
    if (sharpyuv) {
      if (strcmp(canonical, sharp)) {
        fprintf(stderr, "HARMONY_MAPPING_REJECT=sharpyuv_identity; path=%s; canonical=%s; expected=%s\n", path, canonical, sharp);
        foreign = 1; break;
      }
      sharp_seen = 1;
    }
  }
  const int maps_error = ferror(maps); fclose(maps);
  if (maps_error || foreign || !webp_seen || !sharp_seen) {
    fprintf(stderr, "HARMONY_MAPPING_STATE=read_error:%d,foreign:%d,webp_seen:%d,sharpyuv_seen:%d; library=%s; sharpyuv=%s\n", maps_error, foreign, webp_seen, sharp_seen, lib, sharp);
    return fail("foreign_or_ambiguous_mapping");
  }
  printf("{\"actual_loader_and_codec_rc\":0,\"library\":\"%s\","
         "\"webp_mapping\":[\"%s\"],\"sharpyuv_mapping\":[\"%s\"],"
         "\"native_loader\":true,\"width\":1,\"height\":1}\n", lib, lib, sharp);
  if (dlclose(codec) || dlclose(yuv)) return fail("loader_cleanup");
  return 0;
}
