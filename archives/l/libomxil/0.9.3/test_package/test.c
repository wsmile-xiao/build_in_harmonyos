/* test.c — consumer-side verification of libomxil (Bellagio OpenMAX IL 0.9.3).
 *
 * Bellagio's OpenMAX IL core is registry based: OMX_Init() only succeeds when
 * a component registry exists (written by omxregister-bellagio, see the
 * test_package conanfile).  The probe exercises the deployed runtime through
 * the public Khronos IL API, then audits the shipped ELF files for the
 * platform traits HarmonyOS PC requires.  The package folder is taken from
 * $LIBOMXIL_PKG, which the conanfile exports next to $OMX_BELLAGIO_REGISTRY.
 *
 *   [1] OMX_Init() returns OMX_ErrorNone (registry + component loader work)
 *   [2] the registered components are enumerable via OMX_ComponentNameEnum()
 *       and the first one instantiates via OMX_GetHandle()/OMX_FreeHandle()
 *   [3] OMX_Deinit() returns OMX_ErrorNone
 *   [4] HarmonyOS-specific assertions (H1..H8) — the traits that make the
 *       artifact usable on HarmonyOS PC at all:
 *         H1/H2/H3  every shipped ELF is an AArch64 ET_DYN object
 *         H4        bin/omxregister-bellagio is linked against the OHOS
 *                   aarch64 dynamic loader (/lib/ld-linux-aarch64.so.1, the
 *                   name the SDK toolchain bakes in; /lib/ld-musl-aarch64.so.1
 *                   is the same musl runtime), i.e. an OHOS binary and not a
 *                   glibc one
 *         H5        no shipped library needs a glibc-only soname
 *         H6        the IL core needs libc.so only — musl folds pthread/dl in
 *         H7        the packaged loader plugin is dlopen()able by the OHOS
 *                   runtime and exports setup_component_loader
 *         H8        every packaged component library is dlopen()able and
 *                   exports the omx_component_library_Setup entry point the
 *                   core's component loader looks up
 *
 * Exit code 0 means every assertion passed.
 */
#include <OMX_Core.h>

#include <dirent.h>
#include <dlfcn.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>

static int checks;
static int failures;
static int harmonyos_count;
static int consumer_count;
static int in_consumer_group = 1;

#define CHECK(cond, what)                                             \
    do {                                                              \
        checks++;                                                     \
        if (in_consumer_group) {                                      \
            consumer_count++;                                         \
        } else {                                                      \
            harmonyos_count++;                                        \
        }                                                             \
        if (cond) {                                                   \
            printf("  ok   %s\n", what);                              \
        } else {                                                      \
            printf("  FAIL %s (test.c:%d)\n", what, __LINE__);        \
            failures++;                                               \
        }                                                             \
    } while (0)

/* ───────────────────────── ELF64 reader ─────────────────────────
 * The OHOS sysroot is musl based and does ship <elf.h>, but the probe
 * declares the handful of structures it needs so the audit cannot break
 * on a sysroot that does not.  Every shipped object is a little-endian
 * 64-bit AArch64 ELF, which is asserted before anything is parsed.
 */
struct probe_ehdr64 {
    unsigned char e_ident[16];
    uint16_t e_type;
    uint16_t e_machine;
    uint32_t e_version;
    uint64_t e_entry;
    uint64_t e_phoff;
    uint64_t e_shoff;
    uint32_t e_flags;
    uint16_t e_ehsize;
    uint16_t e_phentsize;
    uint16_t e_phnum;
    uint16_t e_shentsize;
    uint16_t e_shnum;
    uint16_t e_shstrndx;
};

struct probe_phdr64 {
    uint32_t p_type;
    uint32_t p_flags;
    uint64_t p_offset;
    uint64_t p_vaddr;
    uint64_t p_paddr;
    uint64_t p_filesz;
    uint64_t p_memsz;
    uint64_t p_align;
};

struct probe_dyn64 {
    int64_t d_tag;
    uint64_t d_val;
};

#define PROBE_PT_LOAD 1
#define PROBE_PT_DYNAMIC 2
#define PROBE_PT_INTERP 3
#define PROBE_DT_NULL 0
#define PROBE_DT_NEEDED 1
#define PROBE_DT_STRTAB 5
#define PROBE_ET_DYN 3
#define PROBE_EM_AARCH64 183
#define PROBE_MAX_NEEDED 16
#define PROBE_MAX_STR 192
#define PROBE_MAX_PATH (PROBE_MAX_STR * 2)

struct probe_elf {
    int parsed;                             /* readable little-endian ELF64 */
    int is_dyn;                             /* e_type == ET_DYN */
    unsigned machine;                       /* e_machine */
    char interp[PROBE_MAX_STR];             /* PT_INTERP, empty when absent */
    int nneeded;
    char needed[PROBE_MAX_NEEDED][PROBE_MAX_STR];
};

/* Read `len` bytes at `off`; 0 on success. */
static int read_at(const char *path, uint64_t off, void *buf, size_t len)
{
    FILE *fh = fopen(path, "rb");
    if (fh == NULL) {
        return -1;
    }
    if (fseek(fh, (long)off, SEEK_SET) != 0
        || fread(buf, 1, len, fh) != len) {
        fclose(fh);
        return -1;
    }
    fclose(fh);
    return 0;
}

/* NUL-terminated string at `off`, truncated to outlen-1 bytes. */
static void read_cstr(const char *path, uint64_t off, char *out, size_t outlen)
{
    FILE *fh;
    size_t i = 0;

    out[0] = '\0';
    fh = fopen(path, "rb");
    if (fh == NULL) {
        return;
    }
    if (fseek(fh, (long)off, SEEK_SET) != 0) {
        fclose(fh);
        return;
    }
    while (i + 1 < outlen) {
        int c = fgetc(fh);
        if (c == EOF || c == '\0') {
            break;
        }
        out[i++] = (char)c;
    }
    out[i] = '\0';
    fclose(fh);
}

static uint64_t vaddr_to_offset(const struct probe_phdr64 *ph, uint64_t count,
                                uint64_t vaddr)
{
    uint64_t i;
    for (i = 0; i < count; i++) {
        if (ph[i].p_type != PROBE_PT_LOAD) {
            continue;
        }
        if (vaddr >= ph[i].p_vaddr && vaddr < ph[i].p_vaddr + ph[i].p_filesz) {
            return ph[i].p_offset + (vaddr - ph[i].p_vaddr);
        }
    }
    return 0;
}

/* Parse header, PT_INTERP and DT_NEEDED of the ELF file `path`. */
static void read_elf(const char *path, struct probe_elf *elf)
{
    struct probe_ehdr64 eh;
    struct probe_phdr64 *ph = NULL;
    uint64_t dyn_off = 0, dyn_size = 0, strtab_vaddr = 0;
    uint64_t i;

    memset(elf, 0, sizeof(*elf));
    if (read_at(path, 0, &eh, sizeof(eh)) != 0) {
        return;
    }
    if (memcmp(eh.e_ident, "\177ELF", 4) != 0 || eh.e_ident[4] != 2
        || eh.e_ident[5] != 1) {
        return;
    }
    if (eh.e_phentsize != sizeof(struct probe_phdr64) || eh.e_phnum == 0) {
        return;
    }
    elf->parsed = 1;
    elf->is_dyn = (eh.e_type == PROBE_ET_DYN);
    elf->machine = eh.e_machine;

    ph = calloc(eh.e_phnum, sizeof(*ph));
    if (ph == NULL
        || read_at(path, eh.e_phoff, ph,
                   (size_t)eh.e_phnum * sizeof(*ph)) != 0) {
        free(ph);
        return;
    }
    for (i = 0; i < eh.e_phnum; i++) {
        if (ph[i].p_type == PROBE_PT_INTERP) {
            uint64_t len = ph[i].p_filesz;
            if (len >= PROBE_MAX_STR) {
                len = PROBE_MAX_STR - 1;
            }
            if (read_at(path, ph[i].p_offset, elf->interp, (size_t)len) == 0) {
                elf->interp[len] = '\0';
            }
        } else if (ph[i].p_type == PROBE_PT_DYNAMIC) {
            dyn_off = ph[i].p_offset;
            dyn_size = ph[i].p_filesz;
        }
    }
    if (dyn_off == 0 || dyn_size == 0) {
        free(ph);
        return;   /* no dynamic section: nothing to audit */
    }
    /* pass 1: locate the dynamic string table */
    for (i = 0; i + sizeof(struct probe_dyn64) <= dyn_size;
         i += sizeof(struct probe_dyn64)) {
        struct probe_dyn64 dyn;
        if (read_at(path, dyn_off + i, &dyn, sizeof(dyn)) != 0) {
            break;
        }
        if (dyn.d_tag == PROBE_DT_NULL) {
            break;
        }
        if (dyn.d_tag == PROBE_DT_STRTAB) {
            strtab_vaddr = dyn.d_val;
            break;
        }
    }
    if (strtab_vaddr == 0) {
        free(ph);
        return;
    }
    /* pass 2: DT_NEEDED holds string-table indices, not addresses */
    for (i = 0; i + sizeof(struct probe_dyn64) <= dyn_size;
         i += sizeof(struct probe_dyn64)) {
        struct probe_dyn64 dyn;
        uint64_t off;
        if (read_at(path, dyn_off + i, &dyn, sizeof(dyn)) != 0) {
            break;
        }
        if (dyn.d_tag == PROBE_DT_NULL) {
            break;
        }
        if (dyn.d_tag != PROBE_DT_NEEDED || elf->nneeded >= PROBE_MAX_NEEDED) {
            continue;
        }
        off = vaddr_to_offset(ph, eh.e_phnum, strtab_vaddr + dyn.d_val);
        if (off == 0) {
            continue;
        }
        read_cstr(path, off, elf->needed[elf->nneeded], PROBE_MAX_STR);
        elf->nneeded++;
    }
    free(ph);
}

/* ───────────────────── package layout helpers ───────────────────── */

/* Longest "lib<prefix>*.so[.*]" entry of `dir`; 0 when there is none. */
static int find_shared_object(const char *dir, const char *stem, char *out,
                              size_t outlen)
{
    DIR *dh = opendir(dir);
    struct dirent *entry;
    char best[PROBE_MAX_STR];
    int found = 0;

    if (dh == NULL) {
        return 0;
    }
    best[0] = '\0';
    while ((entry = readdir(dh)) != NULL) {
        const char *dot;
        if (stem != NULL && strncmp(entry->d_name, stem, strlen(stem))) {
            continue;
        }
        dot = strstr(entry->d_name, ".so");
        if (dot == NULL || (dot[3] != '\0' && dot[3] != '.')) {
            continue;
        }
        if (!found || strlen(entry->d_name) > strlen(best)) {
            snprintf(best, sizeof(best), "%s", entry->d_name);
            found = 1;
        }
    }
    closedir(dh);
    if (!found) {
        return 0;
    }
    snprintf(out, outlen, "%s/%s", dir, best);
    return 1;
}

/* sonames that exist on glibc only; OHOS musl folds them into libc. */
static int is_glibc_only(const char *soname)
{
    static const char *const glibc[] = {
        "libc.so.6", "libpthread.so.0", "libdl.so.2", "libm.so.6",
        "librt.so.1", "libstdc++.so.6", "libgcc_s.so.1", "libresolv.so.2",
        "libutil.so.1", "libnsl.so.1", "libcrypt.so.1", NULL
    };
    int i;
    for (i = 0; glibc[i] != NULL; i++) {
        if (strcmp(soname, glibc[i]) == 0) {
            return 1;
        }
    }
    return 0;
}

/* OHOS ships its musl runtime under both spellings: the SDK toolchain bakes
 * /lib/ld-linux-aarch64.so.1 into every binary, the pure musl convention is
 * /lib/ld-musl-aarch64.so.1.  Either one proves the executable runs on the
 * OHOS aarch64 runtime instead of a host glibc. */
static int is_ohos_loader(const char *interp)
{
    return strcmp(interp, "/lib/ld-linux-aarch64.so.1") == 0
           || strcmp(interp, "/lib/ld-musl-aarch64.so.1") == 0;
}

#define MAX_COMPONENTS 32

static char comp_path[MAX_COMPONENTS][PROBE_MAX_PATH];
static struct probe_elf comp_elf[MAX_COMPONENTS];
static int n_comp;

/* Collect the distinct component libraries of `dir` (libfoo.so, libfoo.so.0
 * and libfoo.so.0.0.0 are one file). */
static void collect_components(const char *dir)
{
    DIR *dh = opendir(dir);
    struct dirent *entry;

    n_comp = 0;
    if (dh == NULL) {
        return;
    }
    while ((entry = readdir(dh)) != NULL && n_comp < MAX_COMPONENTS) {
        const char *dot = strstr(entry->d_name, ".so");
        char path[PROBE_MAX_PATH];
        struct stat sb;
        int duplicate = 0;
        int i;

        if (dot == NULL || (dot[3] != '\0' && dot[3] != '.')) {
            continue;
        }
        snprintf(path, sizeof(path), "%s/%s", dir, entry->d_name);
        if (stat(path, &sb) != 0) {
            continue;
        }
        for (i = 0; i < n_comp; i++) {
            struct stat known;
            if (stat(comp_path[i], &known) == 0
                && known.st_dev == sb.st_dev && known.st_ino == sb.st_ino) {
                duplicate = 1;
                break;
            }
        }
        if (duplicate) {
            continue;
        }
        snprintf(comp_path[n_comp], PROBE_MAX_PATH, "%s", path);
        read_elf(comp_path[n_comp], &comp_elf[n_comp]);
        n_comp++;
    }
    closedir(dh);
}

/* ───────────────────── consumer IL API checks ───────────────────── */

static int consumer_runtime_checks(void)
{
    char first[OMX_MAX_STRINGNAME_SIZE];
    char name[OMX_MAX_STRINGNAME_SIZE];
    OMX_CALLBACKTYPE callbacks;
    OMX_HANDLETYPE handle;
    OMX_ERRORTYPE err;
    int count = 0;

    in_consumer_group = 1;

    printf("[1] OMX_Init\n");
    err = OMX_Init();
    CHECK(err == OMX_ErrorNone, "OMX_Init() returns OMX_ErrorNone");
    if (err != OMX_ErrorNone) {
        return 0;
    }

    printf("[2] component enumeration\n");
    while ((err = OMX_ComponentNameEnum(name, sizeof(name), count))
               == OMX_ErrorNone) {
        printf("  component[%d]: %s\n", count, name);
        count++;
    }
    CHECK(err == OMX_ErrorNoMore,
          "OMX_ComponentNameEnum() ends with OMX_ErrorNoMore");
    CHECK(count >= 3,
          "the Bellagio component set is registered (>= 3 components)");

    if (OMX_ComponentNameEnum(first, sizeof(first), 0) == OMX_ErrorNone) {
        handle = NULL;
        memset(&callbacks, 0, sizeof(callbacks));
        err = OMX_GetHandle(&handle, first, NULL, &callbacks);
        CHECK(err == OMX_ErrorNone && handle != NULL,
              "OMX_GetHandle() instantiates the first component");
        if (err == OMX_ErrorNone && handle != NULL) {
            err = OMX_FreeHandle(handle);
            CHECK(err == OMX_ErrorNone, "OMX_FreeHandle() releases it");
        }
    }

    printf("[3] OMX_Deinit\n");
    err = OMX_Deinit();
    CHECK(err == OMX_ErrorNone, "OMX_Deinit() returns OMX_ErrorNone");
    return 1;
}

/* ─────────────── HarmonyOS-specific checks (H1..H8) ─────────────── */

static void harmonyos_platform_checks(const char *pkg)
{
    char libdir[PROBE_MAX_PATH], compdir[PROBE_MAX_PATH];
    char loaddir[PROBE_MAX_PATH], core[PROBE_MAX_PATH];
    char plugin[PROBE_MAX_PATH], tool[PROBE_MAX_PATH];
    struct probe_elf core_elf, plugin_elf, tool_elf;
    char leak[PROBE_MAX_PATH] = "";
    int have_plugin, aarch64_ok, loaded, i, j;

    in_consumer_group = 0;
    printf("[4] HarmonyOS-specific checks\n");

    snprintf(libdir, sizeof(libdir), "%s/lib", pkg);
    snprintf(compdir, sizeof(compdir), "%s/lib/bellagio", pkg);
    snprintf(loaddir, sizeof(loaddir), "%s/lib/omxloaders", pkg);
    snprintf(tool, sizeof(tool), "%s/bin/omxregister-bellagio", pkg);

    if (!find_shared_object(libdir, "libomxil-bellagio.so", core,
                            sizeof(core))) {
        CHECK(0, "H1: packaged IL core lib/libomxil-bellagio.so* exists");
        return;
    }
    have_plugin = find_shared_object(loaddir, "libomxdynamicloader.so", plugin,
                                     sizeof(plugin));
    read_elf(core, &core_elf);
    read_elf(tool, &tool_elf);
    if (have_plugin) {
        read_elf(plugin, &plugin_elf);
    } else {
        memset(&plugin_elf, 0, sizeof(plugin_elf));
    }
    collect_components(compdir);

    /* H1 — the IL core is an AArch64 shared object */
    CHECK(core_elf.parsed && core_elf.machine == PROBE_EM_AARCH64
              && core_elf.is_dyn,
          "H1: lib/libomxil-bellagio.so* is an AArch64 ELF64 shared object");

    /* H2 — the dynamic loader plugin is an AArch64 shared object */
    CHECK(have_plugin && plugin_elf.parsed
              && plugin_elf.machine == PROBE_EM_AARCH64 && plugin_elf.is_dyn,
          "H2: lib/omxloaders/libomxdynamicloader.so* is an AArch64 ELF64 "
          "shared object");

    /* H3 — every shipped component library is an AArch64 shared object */
    aarch64_ok = (n_comp >= 3);
    for (i = 0; i < n_comp && aarch64_ok; i++) {
        aarch64_ok = comp_elf[i].parsed
                     && comp_elf[i].machine == PROBE_EM_AARCH64
                     && comp_elf[i].is_dyn;
    }
    CHECK(aarch64_ok,
          "H3: every lib/bellagio component is an AArch64 ELF64 shared "
          "object (>= 3 components)");

    /* H4 — the registration tool is linked against the OHOS aarch64 loader */
    CHECK(tool_elf.parsed && is_ohos_loader(tool_elf.interp),
          "H4: bin/omxregister-bellagio uses the OHOS aarch64 loader "
          "(/lib/ld-linux-aarch64.so.1 or /lib/ld-musl-aarch64.so.1)");

    /* H5 — no shipped ELF needs a glibc-only soname */
    for (i = 0; i < n_comp && leak[0] == '\0'; i++) {
        for (j = 0; j < comp_elf[i].nneeded; j++) {
            if (is_glibc_only(comp_elf[i].needed[j])) {
                snprintf(leak, sizeof(leak), "%s needs %s", comp_path[i],
                         comp_elf[i].needed[j]);
                break;
            }
        }
    }
    if (leak[0] == '\0') {
        const struct probe_elf *top[3];
        top[0] = &core_elf;
        top[1] = &plugin_elf;
        top[2] = &tool_elf;
        for (i = 0; i < 3 && leak[0] == '\0'; i++) {
            for (j = 0; j < top[i]->nneeded; j++) {
                if (is_glibc_only(top[i]->needed[j])) {
                    snprintf(leak, sizeof(leak), "packaged ELF needs %s",
                             top[i]->needed[j]);
                    break;
                }
            }
        }
    }
    CHECK(leak[0] == '\0',
          "H5: no packaged ELF needs a glibc-only soname "
          "(libc.so.6/libpthread.so.0/libdl.so.2/...)");

    /* H6 — the IL core needs libc.so only (musl folds pthread and dl in) */
    CHECK(core_elf.nneeded == 1 && strcmp(core_elf.needed[0], "libc.so") == 0,
          "H6: DT_NEEDED of the IL core is exactly libc.so "
          "(musl folds pthread/dl)");

    /* H7 — the packaged loader plugin is loadable by the OHOS runtime.
     *
     * The plugin calls RM_Init(), which is implemented by the IL core
     * (src/omx_reference_resource_manager.c) and is intentionally NOT linked
     * into the plugin (src/dynamic_loader/Makefile.am declares no LIBADD), so
     * the symbol is resolved from the host process at runtime.  In production
     * that host IS the core library — the core dlopen()s its loaders — so load
     * the core first with RTLD_GLOBAL.  A standalone dlopen() of the plugin
     * would demand a symbol the plugin is not supposed to carry, and would fail
     * on any platform, not just OHOS (CI build #61152 caught exactly that).
     */
    loaded = 0;
    if (have_plugin) {
        void *core_handle = dlopen(core, RTLD_NOW | RTLD_GLOBAL);
        void *handle;
        if (core_handle == NULL) {
            printf("  info: dlopen(%s): %s\n", core, dlerror());
        }
        handle = dlopen(plugin, RTLD_NOW | RTLD_LOCAL);
        if (handle != NULL) {
            loaded = dlsym(handle, "setup_component_loader") != NULL;
            dlclose(handle);
        } else {
            printf("  info: dlopen(%s): %s\n", plugin, dlerror());
        }
        if (core_handle != NULL) {
            dlclose(core_handle);
        }
    }
    CHECK(loaded,
          "H7: lib/omxloaders/libomxdynamicloader.so* dlopen()s and exports "
          "setup_component_loader");

    /* H8 — every packaged component library is loadable and exports the
     *     entry point the core's component loader looks up */
    loaded = 0;
    for (i = 0; i < n_comp; i++) {
        void *handle = dlopen(comp_path[i], RTLD_NOW | RTLD_LOCAL);
        if (handle == NULL) {
            printf("  info: dlopen(%s): %s\n", comp_path[i], dlerror());
            continue;
        }
        if (dlsym(handle, "omx_component_library_Setup") != NULL) {
            loaded++;
        }
        dlclose(handle);
    }
    CHECK(loaded >= 3,
          "H8: every lib/bellagio component dlopen()s and exports "
          "omx_component_library_Setup (>= 3 components)");

    printf("  info: %d component librar%s audited in %s\n", n_comp,
           n_comp == 1 ? "y" : "ies", compdir);
}

int main(void)
{
    const char *pkg = getenv("LIBOMXIL_PKG");

    if (pkg == NULL || *pkg == '\0') {
        printf("LIBOMXIL_PKG is not set: run the probe through the conan "
               "test_package, which exports the packaged folder.\n");
        printf("RESULT: FAILED\n");
        return 1;
    }
    printf("package folder: %s\n", pkg);

    if (consumer_runtime_checks() == 0) {
        printf("\n%d checks, %d failure(s)\n", checks, failures);
        printf("RESULT: FAILED\n");
        return 1;
    }
    harmonyos_platform_checks(pkg);

    printf("\n%d checks, %d failure(s) (consumer=%d, harmonyos_specific=%d)\n",
           checks, failures, consumer_count, harmonyos_count);
    if (failures) {
        printf("RESULT: FAILED\n");
        return 1;
    }
    printf("RESULT: PASSED\n");
    return 0;
}
