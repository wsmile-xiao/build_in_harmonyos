/* check_module.c — consumer test for xf86-video-ati 22.0.0 (R34).
 *
 * The package ships two X.Org loadable driver modules
 * (lib/xorg/modules/drivers/ati_drv.so and radeon_drv.so).  These modules
 * resolve their xorg-server symbols (xf86AddDriver, exaOps, ...) from the X
 * server process that dlopens them; OHOS/musl performs eager symbol binding
 * at dlopen time, so a standalone program cannot dlopen the module directly
 * (verified on-device: dlopen fails with "symbol not found" even with
 * RTLD_LAZY).
 *
 * The test therefore performs the same validation the X server's module
 * loader (loader.c) performs, directly on the packaged ELF:
 *   1. the file is a valid ELF64 little-endian shared object for AArch64;
 *   2. it exports the driver's loader entry symbol (atiModuleData /
 *      radeonModuleData) as a defined global symbol;
 *   3. that symbol points to an XF86ModuleVersionInfo record whose
 *      MODINFOSTRING markers, driver name and version fields match the
 *      package (the exact data the X server reads to identify and version-
 *      check a video driver module).
 *
 * Pointer members inside the module image are stored as R_AARCH64_RELATIVE
 * relocations by the OHOS linker (the raw file bytes are zero), so the
 * checker resolves them from .rela.dyn the same way the runtime loader
 * would before validating the record contents.
 *
 * Exit code is bound to the validation result: any packaging, arch or
 * symbol-export error fails the test.
 */
#include <elf.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* The magic marker constants the X server scans module data for
 * (xf86Module.h: MODINFOSTRING1/MODINFOSTRING2). */
#define MODINFOSTRING1 0xef23fdc5u
#define MODINFOSTRING2 0x10dc023au

#define R_AARCH64_RELATIVE_TYPE 1027

/* The first members of XF86ModuleVersionInfo (xf86Module.h) as initialized
 * by the driver: modname, vendor, _modinfo1_, _modinfo2_, xf86version,
 * majorversion, minorversion, patchlevel (CARD8/CARD8/CARD16). */
struct module_version_info_head {
    uint64_t modname;      /* const char * -> "ati" / "radeon" */
    uint64_t vendor;       /* const char * */
    uint32_t modinfo1;     /* MODINFOSTRING1 */
    uint32_t modinfo2;     /* MODINFOSTRING2 */
    uint32_t xf86version;
    uint8_t majorversion;
    uint8_t minorversion;
    uint16_t patchlevel;
};

static unsigned char *g_buf;
static size_t g_size;
static uint64_t *g_reloc_pairs;   /* (r_offset, r_addend) pairs */
static size_t g_reloc_count;

static void fail_free(void)
{
    free(g_buf);
    g_buf = NULL;
    free(g_reloc_pairs);
    g_reloc_pairs = NULL;
}

static int fail(const char *path, const char *msg)
{
    fprintf(stderr, "FAIL: %s: %s\n", path, msg);
    fail_free();
    return 1;
}

/* Translate a virtual address to a file offset using the program headers. */
static const unsigned char *vaddr_to_ptr(uint64_t vaddr)
{
    const Elf64_Ehdr *eh = (const Elf64_Ehdr *)g_buf;
    const Elf64_Phdr *ph = (const Elf64_Phdr *)(g_buf + eh->e_phoff);
    int i;
    for (i = 0; i < eh->e_phnum; i++) {
        if (ph[i].p_type == PT_LOAD &&
            vaddr >= ph[i].p_vaddr &&
            vaddr < ph[i].p_vaddr + ph[i].p_filesz) {
            return g_buf + (ph[i].p_offset + (vaddr - ph[i].p_vaddr));
        }
    }
    return NULL;
}

/* Read a NUL-terminated string at a virtual address. */
static const char *vaddr_string(uint64_t vaddr)
{
    const unsigned char *start = vaddr_to_ptr(vaddr);
    const unsigned char *p = start;
    const unsigned char *end = g_buf + g_size;
    if (!p)
        return NULL;
    while (p < end && *p)
        p++;
    if (p >= end)
        return NULL; /* not NUL-terminated inside the file */
    return (const char *)start;
}

/* Collect R_AARCH64_RELATIVE relocations from all SHT_RELA sections. */
static void load_relocations(void)
{
    const Elf64_Ehdr *eh = (const Elf64_Ehdr *)g_buf;
    const Elf64_Shdr *sh = (const Elf64_Shdr *)(g_buf + eh->e_shoff);
    size_t total = 0, n = 0;
    int i;

    if (eh->e_shoff == 0 || eh->e_shnum == 0)
        return;
    for (i = 0; i < eh->e_shnum; i++) {
        if (sh[i].sh_type == SHT_RELA)
            total += sh[i].sh_size / sizeof(Elf64_Rela);
    }
    if (total == 0)
        return;
    g_reloc_pairs = calloc(total * 2, sizeof(uint64_t));
    if (!g_reloc_pairs)
        return;
    for (i = 0; i < eh->e_shnum; i++) {
        if (sh[i].sh_type != SHT_RELA)
            continue;
        {
            const Elf64_Rela *rela =
                (const Elf64_Rela *)(g_buf + sh[i].sh_offset);
            size_t count = sh[i].sh_size / sizeof(Elf64_Rela);
            size_t j;
            for (j = 0; j < count; j++) {
                if (ELF64_R_TYPE(rela[j].r_info) != R_AARCH64_RELATIVE_TYPE)
                    continue;
                g_reloc_pairs[n * 2] = rela[j].r_offset;
                g_reloc_pairs[n * 2 + 1] = rela[j].r_addend;
                n++;
            }
        }
    }
    g_reloc_count = n;
}

/* Resolve the value of a pointer field at runtime: the loader writes
 * r_addend at r_offset for R_AARCH64_RELATIVE entries; replicate that.  If
 * no relocation matches (pre-linked image), fall back to the raw bytes. */
static int resolve_pointer(uint64_t field_vaddr, uint64_t *out)
{
    size_t i;
    for (i = 0; i < g_reloc_count; i++) {
        if (g_reloc_pairs[i * 2] == field_vaddr) {
            *out = g_reloc_pairs[i * 2 + 1];
            return 1;
        }
    }
    {
        const unsigned char *p = vaddr_to_ptr(field_vaddr);
        if (p) {
            memcpy(out, p, sizeof(*out));
            return 1;
        }
    }
    return 0;
}

/* Find a defined global/weak dynamic symbol by name; returns its st_value. */
static int find_dynsym(const char *name, uint64_t *value)
{
    const Elf64_Ehdr *eh = (const Elf64_Ehdr *)g_buf;
    const Elf64_Shdr *sh = (const Elf64_Shdr *)(g_buf + eh->e_shoff);
    const Elf64_Shdr *dynsym = NULL, *dynstr = NULL;
    int i;

    if (eh->e_shoff == 0 || eh->e_shnum == 0)
        return 0;
    for (i = 0; i < eh->e_shnum; i++) {
        if (sh[i].sh_type == SHT_DYNSYM) {
            dynsym = &sh[i];
            dynstr = &sh[sh[i].sh_link];
            break;
        }
    }
    if (!dynsym || !dynstr)
        return 0;

    {
        const Elf64_Sym *sym =
            (const Elf64_Sym *)(g_buf + dynsym->sh_offset);
        const char *strtab = (const char *)(g_buf + dynstr->sh_offset);
        size_t count = dynsym->sh_size / sizeof(Elf64_Sym);
        size_t j;
        for (j = 0; j < count; j++) {
            const char *symname = strtab + sym[j].st_name;
            if (strcmp(symname, name) != 0)
                continue;
            if (sym[j].st_shndx == SHN_UNDEF)
                continue;
            if (ELF64_ST_BIND(sym[j].st_info) != STB_GLOBAL &&
                ELF64_ST_BIND(sym[j].st_info) != STB_WEAK)
                continue;
            *value = sym[j].st_value;
            return 1;
        }
    }
    return 0;
}

/* Regression guard for the glamor-disabled invariant: the recipe disables
 * glamor (no gbm/mesa on OHOS), which compiles out every gbm API reference
 * in the driver (all uses are USE_GLAMOR-guarded); the sdkdir gbm.h stub
 * only satisfies radeon_dri3.c's #include.  If an upstream change ever
 * reintroduces a gbm dependency, the module would carry undefined gbm_*
 * symbols and only fail at X server dlopen time — fail here instead. */
static int check_no_undefined_gbm(void)
{
    const Elf64_Ehdr *eh = (const Elf64_Ehdr *)g_buf;
    const Elf64_Shdr *sh = (const Elf64_Shdr *)(g_buf + eh->e_shoff);
    const Elf64_Shdr *dynsym = NULL, *dynstr = NULL;
    int i;

    if (eh->e_shoff == 0 || eh->e_shnum == 0)
        return 0;
    for (i = 0; i < eh->e_shnum; i++) {
        if (sh[i].sh_type == SHT_DYNSYM) {
            dynsym = &sh[i];
            dynstr = &sh[sh[i].sh_link];
            break;
        }
    }
    if (!dynsym || !dynstr)
        return 0;

    {
        const Elf64_Sym *sym =
            (const Elf64_Sym *)(g_buf + dynsym->sh_offset);
        const char *strtab = (const char *)(g_buf + dynstr->sh_offset);
        size_t count = dynsym->sh_size / sizeof(Elf64_Sym);
        size_t j;
        for (j = 0; j < count; j++) {
            const char *symname;
            if (sym[j].st_shndx != SHN_UNDEF || sym[j].st_name == 0)
                continue;
            symname = strtab + sym[j].st_name;
            if (strncmp(symname, "gbm_", 4) == 0) {
                fprintf(stderr, "FAIL: module references undefined gbm "
                                "symbol '%s' (glamor must stay disabled or "
                                "gbm must be provided)\n", symname);
                return 1;
            }
        }
    }
    return 0;
}

static int check_module(const char *path, const char *symbol,
                        const char *driver_name, uint8_t major, uint8_t minor,
                        uint16_t patch)
{
    const Elf64_Ehdr *eh;
    uint64_t symval, rec, modname_ptr;
    const struct module_version_info_head *vi;
    const char *modname;
    FILE *f;

    f = fopen(path, "rb");
    if (!f)
        return fail(path, "cannot open module file");
    fseek(f, 0, SEEK_END);
    g_size = (size_t)ftell(f);
    fseek(f, 0, SEEK_SET);
    if (g_size < sizeof(Elf64_Ehdr)) {
        fclose(f);
        return fail(path, "file too small to be an ELF object");
    }
    g_buf = malloc(g_size);
    if (!g_buf || fread(g_buf, 1, g_size, f) != g_size) {
        fclose(f);
        return fail(path, "cannot read module file");
    }
    fclose(f);

    eh = (const Elf64_Ehdr *)g_buf;
    if (memcmp(eh->e_ident, ELFMAG, SELFMAG) != 0)
        return fail(path, "not an ELF file");
    if (eh->e_ident[EI_CLASS] != ELFCLASS64)
        return fail(path, "not an ELF64 object");
    if (eh->e_ident[EI_DATA] != ELFDATA2LSB)
        return fail(path, "not little-endian");
    if (eh->e_type != ET_DYN)
        return fail(path, "not a shared object (driver module expected)");
    if (eh->e_machine != EM_AARCH64)
        return fail(path, "not an AArch64 object");

    load_relocations();

    if (check_no_undefined_gbm())
        return 1;

    if (!find_dynsym(symbol, &symval)) {
        fprintf(stderr, "FAIL: %s: loader entry symbol '%s' is not exported "
                        "as a defined global symbol\n", path, symbol);
        fail_free();
        return 1;
    }

    /* atiModuleData/radeonModuleData is an XF86ModuleData record whose first
     * member points at the driver's XF86ModuleVersionInfo. */
    if (!resolve_pointer(symval, &rec))
        return fail(path, "cannot resolve the XF86ModuleData version "
                          "record pointer");
    vi = (const struct module_version_info_head *)vaddr_to_ptr(rec);
    if (!vi)
        return fail(path, "cannot map XF86ModuleVersionInfo record");

    if (vi->modinfo1 != MODINFOSTRING1 || vi->modinfo2 != MODINFOSTRING2)
        return fail(path, "XF86ModuleVersionInfo MODINFOSTRING markers "
                          "do not match xf86Module.h constants");

    if (!resolve_pointer(rec, &modname_ptr))
        return fail(path, "cannot resolve the module name pointer");
    modname = vaddr_string(modname_ptr);
    if (!modname || strcmp(modname, driver_name) != 0) {
        fprintf(stderr, "FAIL: %s: module name is '%s' (expected '%s')\n",
                path, modname ? modname : "()", driver_name);
        fail_free();
        return 1;
    }

    if (vi->majorversion != major || vi->minorversion != minor ||
        vi->patchlevel != patch) {
        fprintf(stderr, "FAIL: %s: module version is %u.%u.%u "
                        "(expected %u.%u.%u)\n",
                path, vi->majorversion, vi->minorversion, vi->patchlevel,
                major, minor, patch);
        fail_free();
        return 1;
    }

    printf("PASS: %s: AArch64 ELF module exporting %s (driver \"%s\", "
           "version %u.%u.%u)\n", path, symbol, modname, vi->majorversion,
           vi->minorversion, vi->patchlevel);
    fail_free();
    return 0;
}

int main(int argc, char **argv)
{
    if (argc != 7) {
        fprintf(stderr,
                "usage: %s <module.so> <symbol> <driver-name> "
                "<major> <minor> <patch>\n"
                "example: %s ati_drv.so atiModuleData ati 22 0 0\n",
                argv[0], argv[0]);
        return 2;
    }
    return check_module(argv[1], argv[2], argv[3],
                        (uint8_t)strtoul(argv[4], NULL, 10),
                        (uint8_t)strtoul(argv[5], NULL, 10),
                        (uint16_t)strtoul(argv[6], NULL, 10));
}
