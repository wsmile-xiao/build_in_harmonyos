/*
 * test_savage.c — Test for the xf86-video-savage driver module.
 *
 * X.Org driver modules are loaded by the X server at runtime, so the
 * module intentionally leaves server symbols (xf86*, pci_device_*,
 * VBE*) unresolved — dlopen() without a running X server would fail
 * on those data relocations. The test therefore verifies the module's
 * dynamic symbol table directly:
 *
 *   1. It is a valid ELF64 ET_DYN AArch64 shared object.
 *   2. It exports the symbols the X server loader requires:
 *      - "savageModuleData"  — the XF86ModuleData entry point every
 *        X.Org module must export (looked up by the loader),
 *      - "SAVAGE"            — the DriverRec of this driver,
 *      - "SavageGetBIOSModeTable" — implemented in savage_vbe.c; its
 *        presence proves the full VBE/BIOS code path is compiled in
 *        (not stubbed out).
 *   3. The dynamic symbol table is non-empty (real code, not an empty
 *      shell).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <stdint.h>
#include <sys/stat.h>
#include <elf.h>

static const char *required_symbols[] = {
    "savageModuleData",
    "SAVAGE",
    "SavageGetBIOSModeTable",
};

/* Load the whole file into memory. */
static unsigned char *read_file(const char *path, size_t *size_out)
{
    FILE *f = fopen(path, "rb");
    struct stat st;
    unsigned char *buf;

    if (!f) return NULL;
    if (fstat(fileno(f), &st) != 0 || st.st_size < (off_t)sizeof(Elf64_Ehdr)) {
        fclose(f);
        return NULL;
    }
    buf = malloc((size_t)st.st_size);
    if (!buf) { fclose(f); return NULL; }
    if (fread(buf, 1, (size_t)st.st_size, f) != (size_t)st.st_size) {
        free(buf); fclose(f); return NULL;
    }
    fclose(f);
    *size_out = (size_t)st.st_size;
    return buf;
}

/* Look up a symbol name in .dynsym. */
static int has_symbol(const Elf64_Sym *symtab, size_t nsyms,
                      const char *strtab, size_t strtab_size, const char *name)
{
    size_t i;
    for (i = 0; i < nsyms; i++) {
        Elf64_Word off = symtab[i].st_name;
        if (off < strtab_size &&
            strcmp(strtab + off, name) == 0 &&
            symtab[i].st_shndx != SHN_UNDEF) {
            return 1;
        }
    }
    return 0;
}

int main(int argc, char **argv)
{
    const char *so_path;
    unsigned char *buf;
    size_t size, i;
    const Elf64_Ehdr *ehdr;
    const Elf64_Shdr *shdrs;
    const char *shstrtab = NULL;
    const Elf64_Sym *dynsym = NULL;
    const char *dynstr = NULL;
    size_t dynsym_count = 0, dynstr_size = 0;
    int failures = 0;

    if (argc < 2) {
        fprintf(stderr, "Usage: %s <path-to-savage_drv.so>\n", argv[0]);
        return 1;
    }
    so_path = argv[1];

    /* Test 1: file exists and is non-empty */
    buf = read_file(so_path, &size);
    if (!buf) {
        fprintf(stderr, "FAIL: cannot read %s\n", so_path);
        return 1;
    }
    printf("PASS: savage_drv.so readable (%zu bytes)\n", size);

    ehdr = (const Elf64_Ehdr *)buf;

    /* Test 2: ELF identity */
    if (memcmp(ehdr->e_ident, ELFMAG, SELFMAG) != 0) {
        fprintf(stderr, "FAIL: not an ELF file\n");
        return 1;
    }
    printf("PASS: valid ELF magic\n");

    /* Test 3: 64-bit shared library for AArch64 */
    if (ehdr->e_ident[EI_CLASS] != ELFCLASS64) {
        fprintf(stderr, "FAIL: not 64-bit ELF (class=%d)\n",
                ehdr->e_ident[EI_CLASS]);
        return 1;
    }
    if (ehdr->e_type != ET_DYN) {
        fprintf(stderr, "FAIL: not a shared library (type=%d)\n", ehdr->e_type);
        return 1;
    }
    if (ehdr->e_machine != EM_AARCH64) {
        fprintf(stderr, "FAIL: not AArch64 (machine=%d)\n", ehdr->e_machine);
        return 1;
    }
    printf("PASS: 64-bit AArch64 shared library (ET_DYN)\n");

    /* Test 4: locate .dynsym/.dynstr through the section headers */
    shdrs = (const Elf64_Shdr *)(buf + ehdr->e_shoff);
    if (ehdr->e_shoff == 0 || ehdr->e_shnum == 0) {
        fprintf(stderr, "FAIL: no section header table\n");
        return 1;
    }
    if (ehdr->e_shstrndx < ehdr->e_shnum) {
        shstrtab = (const char *)(buf + shdrs[ehdr->e_shstrndx].sh_offset);
    }
    for (i = 0; i < ehdr->e_shnum; i++) {
        const char *secname = shstrtab + shdrs[i].sh_name;
        if (strcmp(secname, ".dynsym") == 0) {
            dynsym = (const Elf64_Sym *)(buf + shdrs[i].sh_offset);
            dynsym_count = shdrs[i].sh_size / sizeof(Elf64_Sym);
        } else if (strcmp(secname, ".dynstr") == 0) {
            dynstr = (const char *)(buf + shdrs[i].sh_offset);
            dynstr_size = shdrs[i].sh_size;
        }
    }
    if (!dynsym || !dynstr || dynsym_count == 0) {
        fprintf(stderr, "FAIL: dynamic symbol table missing or empty\n");
        return 1;
    }
    printf("PASS: dynamic symbol table present (%zu symbols)\n", dynsym_count);

    /* Test 5: the symbols the X server loader requires are exported */
    for (i = 0; i < sizeof(required_symbols) / sizeof(required_symbols[0]); i++) {
        if (has_symbol(dynsym, dynsym_count, dynstr, dynstr_size,
                       required_symbols[i])) {
            printf("PASS: exports %s\n", required_symbols[i]);
        } else {
            fprintf(stderr, "FAIL: missing exported symbol %s\n",
                    required_symbols[i]);
            failures++;
        }
    }

    if (failures) {
        fprintf(stderr, "%d symbol check(s) failed\n", failures);
        return 1;
    }
    printf("All tests passed\n");
    return 0;
}
