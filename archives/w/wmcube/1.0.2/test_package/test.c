/*
 * test_package/test.c — wmcube 1.0.2 L1 test harness (R34: real artifact
 * verification, no stub assertions).
 *
 * wmcube is an X11 dockapp.  A CI worker has no X server, so the runtime
 * surface of the produced binary cannot be exercised here (see notes.md):
 * `wmcube` without arguments reaches XOpenDisplay and aborts.  What can be
 * verified mechanically — and what this harness therefore checks — is that
 * the packaged binary is a real AArch64 ELF image, that it is dynamically
 * linked against exactly the three X libraries the upstream Makefile asks
 * for (-lXpm -lXext -lX11), and that the documented command-line surface
 * and version really got compiled into it.
 *
 * The ELF64 structures are declared locally on purpose: the test package is
 * built without any generator, so <elf.h> availability must not be assumed.
 */
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#ifndef WMCUBE_BIN
#define WMCUBE_BIN "wmcube"
#endif

#define EM_AARCH64     183
#define ELFCLASS64     2
#define ELFDATA2LSB    1
#define ET_EXEC        2
#define ET_DYN         3
#define SHT_DYNAMIC    6
#define DT_NULL        0
#define DT_NEEDED      1

typedef struct {
    uint8_t  e_ident[16];
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
} Elf64_Ehdr;

typedef struct {
    uint32_t sh_name;
    uint32_t sh_type;
    uint64_t sh_flags;
    uint64_t sh_addr;
    uint64_t sh_offset;
    uint64_t sh_size;
    uint32_t sh_link;
    uint32_t sh_info;
    uint64_t sh_addralign;
    uint64_t sh_entsize;
} Elf64_Shdr;

typedef struct {
    uint64_t d_tag;
    uint64_t d_val;
} Elf64_Dyn;

static int g_total = 0;
static int g_failed = 0;

static void check(int ok, const char *what, const char *detail)
{
    g_total++;
    if (ok) {
        printf("  [PASS] %-46s %s\n", what, detail ? detail : "");
    } else {
        g_failed++;
        printf("  [FAIL] %-46s %s\n", what, detail ? detail : "");
    }
}

/* Substring search inside the raw file image (covers .rodata strings). */
static int image_contains(const unsigned char *buf, size_t n, const char *s)
{
    size_t len = strlen(s);
    size_t i;

    if (len == 0 || n < len)
        return 0;
    for (i = 0; i + len <= n; i++) {
        if (memcmp(buf + i, s, len) == 0)
            return 1;
    }
    return 0;
}

static int needed_has(const char *needed[], int count, const char *frag)
{
    int i;

    for (i = 0; i < count; i++)
        if (needed[i] && strstr(needed[i], frag) != NULL)
            return 1;
    return 0;
}

int main(void)
{
    const char *path = WMCUBE_BIN;
    FILE *fp;
    long size;
    unsigned char *buf;
    const Elf64_Ehdr *eh;
    const Elf64_Shdr *sh;
    const Elf64_Dyn *dyn;
    const char *strtab;
    const char *needed[32];
    int i, dyn_index = -1, needed_count = 0, dyn_entries = 0;
    size_t dyn_size = 0;

    printf("wmcube 1.0.2 L1 test harness — target: %s\n", path);

    fp = fopen(path, "rb");
    if (fp == NULL) {
        perror("fopen(packaged binary)");
        printf("RESULT: FAIL (0/0) — packaged binary not readable\n");
        return 1;
    }
    if (fseek(fp, 0, SEEK_END) != 0) {
        perror("fseek");
        fclose(fp);
        return 1;
    }
    size = ftell(fp);
    rewind(fp);
    if (size < (long)sizeof(Elf64_Ehdr)) {
        printf("RESULT: FAIL — file too small to be an ELF image (%ld bytes)\n", size);
        fclose(fp);
        return 1;
    }
    buf = malloc((size_t)size);
    if (buf == NULL) {
        printf("RESULT: FAIL — out of memory\n");
        fclose(fp);
        return 1;
    }
    if (fread(buf, 1, (size_t)size, fp) != (size_t)size) {
        printf("RESULT: FAIL — short read\n");
        free(buf);
        fclose(fp);
        return 1;
    }
    fclose(fp);

    eh = (const Elf64_Ehdr *)buf;
    sh = (const Elf64_Shdr *)(buf + eh->e_shoff);
    strtab = NULL;

    /* ---- image / ELF identity ---- */
    check(buf[0] == 0x7f && buf[1] == 'E' && buf[2] == 'L' && buf[3] == 'F',
          "A1 ELF magic", "elf_ident");
    check(eh->e_ident[4] == ELFCLASS64,
          "A2 ELF class is 64-bit", "ELFCLASS64");
    check(eh->e_ident[5] == ELFDATA2LSB,
          "A3 ELF data order is little-endian", "ELFDATA2LSB");
    check(eh->e_machine == EM_AARCH64,
          "A4 e_machine == EM_AARCH64 (AArch64)", "arm64 target");
    check(eh->e_type == ET_EXEC || eh->e_type == ET_DYN,
          "A5 e_type is ET_EXEC or ET_DYN (runnable image)", NULL);
    check(eh->e_shoff != 0 && eh->e_shnum > 0 &&
          (long)(eh->e_shoff + (uint64_t)eh->e_shnum * eh->e_shentsize) <= size,
          "A6 section header table lies inside the file", NULL);

    /* ---- dynamic section / library closure ---- */
    if (eh->e_shoff == 0 || eh->e_shnum == 0) {
        for (i = 0; i < 10; i++)
            check(0, "A7..A16 skipped: no section headers", NULL);
    } else {
        for (i = 0; i < eh->e_shnum; i++) {
            if (sh[i].sh_type == SHT_DYNAMIC) {
                dyn_index = i;
                break;
            }
        }
        check(dyn_index >= 0, "A7 .dynamic section present (shared-library image)", NULL);

        if (dyn_index >= 0) {
            dyn_size = (size_t)sh[dyn_index].sh_size;
            dyn_entries = (int)(dyn_size / sizeof(Elf64_Dyn));
            strtab = (const char *)buf + sh[sh[dyn_index].sh_link].sh_offset;
            check(dyn_index >= 0 && sh[dyn_index].sh_link < eh->e_shnum &&
                  dyn_entries > 0 &&
                  sh[sh[dyn_index].sh_link].sh_offset + sh[sh[dyn_index].sh_link].sh_size
                      <= (uint64_t)size,
                  "A8 dynamic strtab resolves inside the file", NULL);

            dyn = (const Elf64_Dyn *)(buf + sh[dyn_index].sh_offset);
            for (i = 0; i < dyn_entries && dyn[i].d_tag != DT_NULL; i++) {
                if (dyn[i].d_tag == DT_NEEDED && needed_count < 32) {
                    needed[needed_count++] = strtab + dyn[i].d_val;
                    printf("       DT_NEEDED[%d] = %s\n", needed_count,
                           needed[needed_count - 1]);
                }
            }
            check(needed_count > 0, "A9 DT_NEEDED list is not empty", NULL);
            check(needed_has(needed, needed_count, "X11"),
                  "A10 linked against libX11 (upstream -lX11)", NULL);
            check(needed_has(needed, needed_count, "Xext"),
                  "A11 linked against libXext (XShapeCombineMask)", NULL);
            check(needed_has(needed, needed_count, "Xpm"),
                  "A12 linked against libXpm (XpmCreatePixmapFromData)", NULL);
        }
    }

    /* ---- compiled-in command-line surface / version / data path ---- */
    check(image_contains(buf, (size_t)size, "Usage: wmcube [-o <filename>]"),
          "A13 usage banner compiled in (-h surface)", NULL);
    check(image_contains(buf, (size_t)size, "1.0.2"),
          "A14 upstream version string CK_WMCUBE_VERSION == 1.0.2", NULL);
    check(image_contains(buf, (size_t)size, "load external 3D object (plugin)"),
          "A15 -o option help text compiled in", NULL);
    check(image_contains(buf, (size_t)size, "/usr/share/wmcube/"),
          "A16 default 3D-object directory literal present", "see notes.md");

    printf("RESULT: %s (%d/%d assertions passed, %d failed)\n",
           g_failed == 0 ? "PASS" : "FAIL", g_total - g_failed, g_total, g_failed);
    free(buf);
    return g_failed == 0 ? 0 : 1;
}
