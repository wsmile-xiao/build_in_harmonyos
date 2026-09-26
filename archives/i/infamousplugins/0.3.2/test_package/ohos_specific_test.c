/* ohos_specific_test.c — HarmonyOS (OHOS) specific validation of the packaged
 * infamousPlugins LV2 bundles.
 *
 * This test covers the platform properties that the generic consumer test
 * (test_lv2_plugins.c) does not:
 *
 *   P1  Target/platform: the test itself must be AArch64 LP64 and the kernel
 *       must report machine aarch64.
 *   P2  OHOS ELF constraints: every <plug>.so is a 64-bit AArch64 shared object
 *       (ELFCLASS64 / EM_AARCH64 / ET_DYN).  OHOS only executes ELF images with
 *       the expected machine class, so this is checked header by header.
 *   P3  Loadable image: each plug-in is dlopen()ed with RTLD_NOW straight from
 *       the Conan package directory.  This is the OHOS-critical assertion — OHOS
 *       refuses to map an ELF that is not properly formed/signed, and RTLD_NOW
 *       also has to resolve every DT_NEEDED library and every symbol.
 *   P4  Origin: dladdr() on the plug-in's own entry point must report the
 *       package path that was passed to dlopen(), i.e. the code executing is the
 *       one shipped by this package and not a stale system copy.
 *   P5  Conan shared dependency chain: after the bundles are loaded,
 *       libzita-resampler / libfftw3f (DT_NEEDED of ewham and lushlife) are
 *       already mapped (RTLD_NOLOAD), i.e. the conanrun environment resolves the
 *       dependency chain at run time on OHOS.
 *   P6  Shared-prefix hygiene: no plug-in contains the literal "/usr/local"
 *       path, so the package can never load a library from the shared worker
 *       prefix instead of its own Conan dependency (R49 / E524 class).
 *   P7  LV2 bundle layout: lib/lv2/<plug>.lv2/{manifest.ttl,<plug>.so,<plug>.ttl}.
 *
 * Usage: ohos_specific_test <lv2-bundle-root>
 * Prints one "TEST_RESULT={...}" JSON line for the driver to collect.
 */
#define _GNU_SOURCE
#include <dirent.h>
#include <dlfcn.h>
#include <elf.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/utsname.h>

#define MAX_BUNDLES 64

static int g_checks;
static int g_failed;

static void check(int cond, const char *what, const char *detail)
{
    g_checks++;
    if (cond) {
        printf("  ok   %s%s%s\n", what, detail && *detail ? ": " : "",
               detail && *detail ? detail : "");
    } else {
        g_failed++;
        printf("  FAIL %s%s%s\n", what, detail && *detail ? ": " : "",
               detail && *detail ? detail : "");
    }
}

static char *slurp(const char *path)
{
    FILE *f = fopen(path, "rb");
    if (!f)
        return NULL;
    if (fseek(f, 0, SEEK_END) != 0) {
        fclose(f);
        return NULL;
    }
    long size = ftell(f);
    if (size < 0) {
        fclose(f);
        return NULL;
    }
    rewind(f);
    char *buf = malloc((size_t)size + 1);
    if (!buf) {
        fclose(f);
        return NULL;
    }
    size_t got = fread(buf, 1, (size_t)size, f);
    buf[got] = '\0';
    fclose(f);
    return buf;
}

static int file_exists(const char *path)
{
    FILE *f = fopen(path, "rb");
    if (!f)
        return 0;
    fclose(f);
    return 1;
}

/* Pull the DT_NEEDED soname for a library whose name starts with `prefix` out
 * of the .dynstr section of a shared object (the strings are always NUL
 * terminated there).  Returns 1 and fills `out` when the dependency is present. */
static int declared_soname(const char *bytes, size_t len, const char *prefix,
                           char *out, size_t out_size)
{
    size_t prefix_len = strlen(prefix);
    for (size_t i = 0; i + prefix_len < len; i++) {
        if (memcmp(bytes + i, prefix, prefix_len) != 0)
            continue;
        size_t j = 0;
        while (i + j < len && bytes[i + j] != '\0' && j + 1 < out_size) {
            out[j] = bytes[i + j];
            j++;
        }
        out[j] = '\0';
        return j > prefix_len;
    }
    return 0;
}

int main(int argc, char **argv)
{
    /* keep the log usable when the program dies in a plug-in */
    setvbuf(stdout, NULL, _IOLBF, 0);
    if (argc != 2) {
        fprintf(stderr, "usage: %s <lv2-bundle-root>\n", argv[0]);
        return 2;
    }
    const char *root = argv[1];
    char detail[1200];

    /* ── P1: platform ── */
#if defined(__aarch64__) && defined(__LP64__)
    check(1, "test built for AArch64 LP64", "");
#else
    check(0, "test built for AArch64 LP64", "wrong target triple");
#endif
    check(sizeof(void *) == 8, "64-bit data model", "");

    struct utsname uname_buf;
    if (uname(&uname_buf) == 0) {
        snprintf(detail, sizeof(detail), "%s %s %s", uname_buf.sysname,
                 uname_buf.release, uname_buf.machine);
        check(strcmp(uname_buf.machine, "aarch64") == 0, "kernel machine is aarch64", detail);
    } else {
        check(0, "uname() readable", "uname failed");
    }

    char names[MAX_BUNDLES][256];
    int bundles = 0;
    DIR *dir = opendir(root);
    if (!dir) {
        fprintf(stderr, "FAIL: cannot open LV2 bundle root %s\n", root);
        return 2;
    }
    struct dirent *entry;
    while ((entry = readdir(dir)) != NULL) {
        size_t n = strlen(entry->d_name);
        if (n < 5 || strcmp(entry->d_name + n - 4, ".lv2") != 0)
            continue;
        if (bundles >= MAX_BUNDLES)
            break;
        snprintf(names[bundles++], 256, "%s", entry->d_name);
    }
    closedir(dir);
    check(bundles > 0, "bundle root contains at least one .lv2 bundle", root);

    for (int b = 0; b < bundles; b++) {
        char plug[256];
        char bundle_dir[1024], so_path[1024], ttl_path[1024], manifest_path[1024];
        snprintf(plug, sizeof(plug), "%s", names[b]);
        plug[strlen(plug) - 4] = '\0';
        snprintf(bundle_dir, sizeof(bundle_dir), "%s/%s", root, names[b]);
        snprintf(so_path, sizeof(so_path), "%s/%s.so", bundle_dir, plug);
        snprintf(ttl_path, sizeof(ttl_path), "%s/%s.ttl", bundle_dir, plug);
        snprintf(manifest_path, sizeof(manifest_path), "%s/manifest.ttl", bundle_dir);

        printf("--- %s\n", names[b]);

        /* ── P7: bundle layout ── */
        check(file_exists(manifest_path), "bundle manifest.ttl present", manifest_path);
        check(file_exists(ttl_path), "bundle plug-in .ttl present", ttl_path);
        check(file_exists(so_path), "bundle .so present", so_path);

        /* ── P2: ELF identity ── */
        FILE *bin = fopen(so_path, "rb");
        if (!bin) {
            check(0, "plug-in binary readable", so_path);
            continue;
        }
        Elf64_Ehdr eh;
        memset(&eh, 0, sizeof(eh));
        size_t hdr = fread(&eh, 1, sizeof(eh), bin);
        fseek(bin, 0, SEEK_END);
        long file_size = ftell(bin);
        rewind(bin);
        char *bytes = malloc((size_t)(file_size > 0 ? file_size : 0) + 1);
        size_t read_bytes = 0;
        if (bytes) {
            read_bytes = fread(bytes, 1, (size_t)file_size, bin);
            bytes[read_bytes] = '\0';
        }
        fclose(bin);

        check(hdr == sizeof(eh) && memcmp(eh.e_ident, ELFMAG, SELFMAG) == 0,
              "ELF magic", plug);
        check(hdr == sizeof(eh) && eh.e_ident[EI_CLASS] == ELFCLASS64,
              "ELFCLASS64", plug);
        check(hdr == sizeof(eh) && eh.e_machine == EM_AARCH64,
              "EM_AARCH64 machine", plug);
        check(hdr == sizeof(eh) && eh.e_type == ET_DYN,
              "ET_DYN shared object", plug);

        /* ── P6: no shared-prefix (/usr/local) path baked into the plug-in ── */
        if (bytes) {
            snprintf(detail, sizeof(detail), "%s (%ld bytes scanned)", plug, file_size);
            check(memmem(bytes, read_bytes, "/usr/local", 10) == NULL,
                  "no \"/usr/local\" path baked into the binary", detail);
        } else {
            check(0, "plug-in binary readable for path scan", so_path);
        }

        /* ── P3: OHOS must be able to map and resolve the image ── */
        void *handle = dlopen(so_path, RTLD_NOW | RTLD_LOCAL);
        if (!handle) {
            check(0, "dlopen(RTLD_NOW) from Conan package", dlerror());
            free(bytes);
            continue;
        }
        check(1, "dlopen(RTLD_NOW) from Conan package", so_path);

        /* ── P4: the executing image really comes from the package ── */
        void *entry = dlsym(handle, "lv2_descriptor");
        Dl_info info;
        memset(&info, 0, sizeof(info));
        if (!entry) {
            check(0, "plug-in entry point resolvable", dlerror());
        } else if (dladdr(entry, &info) == 0 || info.dli_fname == NULL) {
            check(0, "dladdr() reports the plug-in image", "dladdr failed");
        } else {
            snprintf(detail, sizeof(detail), "%s", info.dli_fname);
            check(strcmp(info.dli_fname, so_path) == 0,
                  "plug-in image loaded from the Conan package", detail);
        }

        /* ── P5: the Conan shared dependency chain is really resolved ──
         * Checked while this plug-in is still loaded: the sonames declared as
         * DT_NEEDED must already be mapped (RTLD_NOLOAD). */
        if (bytes) {
            static const char *conan_deps[] = {"libzita-resampler.so", "libfftw3f.so"};
            for (size_t d = 0; d < sizeof(conan_deps) / sizeof(conan_deps[0]); d++) {
                char soname[256];
                if (!declared_soname(bytes, read_bytes, conan_deps[d], soname, sizeof(soname)))
                    continue;
#ifdef RTLD_NOLOAD
                void *dep = dlopen(soname, RTLD_NOW | RTLD_NOLOAD);
#else
                void *dep = NULL;
#endif
                check(dep != NULL, "declared Conan dependency is mapped", soname);
                if (dep)
                    dlclose(dep);
            }
        }

        free(bytes);
        dlclose(handle);
    }

    printf("TEST_RESULT={\"bundles\":%d,\"discovered\":%d,\"passed\":%d,\"failed\":%d}\n",
           bundles, g_checks, g_checks - g_failed, g_failed);
    printf("%s: %d/%d OHOS specific checks passed\n", g_failed ? "FAIL" : "PASS",
           g_checks - g_failed, g_checks);
    return g_failed ? 1 : 0;
}
