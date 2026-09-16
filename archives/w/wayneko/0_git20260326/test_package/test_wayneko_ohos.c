/* test_wayneko_ohos.c — HarmonyOS-specific consumer test for wayneko.
 *
 * This test is built ONLY when the target OS is OHOS (compile-time guard
 * below) and asserts OHOS/platform properties of the INSTALLED wayneko
 * binary produced by the Conan package:
 *
 *   - valid ELF64 little-endian AArch64 image (OHOS armv8 target)
 *   - position-independent executable (PIE, ET_DYN) — the OHOS loader and
 *     ASLR require PIE executables
 *   - dynamically linked (PT_INTERP present)
 *   - non-executable stack (NX) and RELRO present (OHOS security baseline)
 *   - links libwayland-client and libpixman-1 — proves the resolved Conan
 *     dependency chain is embedded in the artifact (R26/R49 检查)
 *   - carries NO undefined reference to glibc `backtrace` /
 *     `backtrace_symbols_fd`: wayneko.c guards that block with
 *     `#ifdef __GLIBC__` (lines 17-22), and OHOS (musl-based) must not link
 *     glibc-only symbols — this asserts the OHOS portability adaptation is
 *     actually effective in the shipped binary.
 *
 * Assertion count: 12. Exit code 0 iff all pass.
 */
#ifndef __OHOS__
#error "test_wayneko_ohos.c must be compiled for HarmonyOS (OHOS)"
#endif

#include <elf.h>
#include <errno.h>
#include <fcntl.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/mman.h>
#include <sys/stat.h>
#include <unistd.h>

static int g_pass = 0;
static int g_fail = 0;

static void check(int cond, const char *name)
{
    if (cond) {
        g_pass++;
        printf("  [ok]   %s\n", name);
    } else {
        g_fail++;
        printf("  [FAIL] %s\n", name);
    }
}

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s <installed-wayneko-binary>\n", argv[0]);
        return 2;
    }
    const char *path = argv[1];

    int fd = open(path, O_RDONLY);
    if (fd < 0) {
        fprintf(stderr, "cannot open %s: %s\n", path, strerror(errno));
        return 2;
    }
    struct stat st;
    if (fstat(fd, &st) != 0) {
        perror("fstat");
        close(fd);
        return 2;
    }
    void *map = mmap(NULL, (size_t)st.st_size, PROT_READ, MAP_PRIVATE, fd, 0);
    if (map == MAP_FAILED) {
        perror("mmap");
        close(fd);
        return 2;
    }
    close(fd);

    const unsigned char *bytes = (const unsigned char *)map;
    const Elf64_Ehdr *eh = (const Elf64_Ehdr *)bytes;

    check(st.st_size >= (off_t)sizeof(Elf64_Ehdr), "ELF header fits in file");
    check(eh->e_ident[EI_MAG0] == ELFMAG0 && eh->e_ident[EI_MAG1] == ELFMAG1 &&
              eh->e_ident[EI_MAG2] == ELFMAG2 && eh->e_ident[EI_MAG3] == ELFMAG3,
          "valid ELF magic");
    check(eh->e_ident[EI_CLASS] == ELFCLASS64, "ELF64 class");
    check(eh->e_ident[EI_DATA] == ELFDATA2LSB, "little-endian (ELFDATA2LSB)");
    check(eh->e_machine == EM_AARCH64, "AArch64 machine (EM_AARCH64)");
    check(eh->e_type == ET_DYN, "PIE executable (ET_DYN)");

    /* ── program headers: interpreter / NX / RELRO ── */
    int has_interp = 0;
    int has_stack = 0;
    int stack_nx = 1;
    int has_relro = 0;
    for (int i = 0; i < eh->e_phnum; i++) {
        const Elf64_Phdr *ph = (const Elf64_Phdr *)(bytes + eh->e_phoff +
                                                    (Elf64_Off)i * sizeof(Elf64_Phdr));
        if (ph->p_type == PT_INTERP) {
            has_interp = 1;
        } else if (ph->p_type == PT_GNU_STACK) {
            has_stack = 1;
            if (ph->p_flags & PF_X) {
                stack_nx = 0;
            }
        } else if (ph->p_type == PT_GNU_RELRO) {
            has_relro = 1;
        }
    }

    /* ── section headers: dynamic tags + dynamic symbol table ── */
    Elf64_Off dyn_off = 0;
    Elf64_Xword dyn_sz = 0;
    int dyn_strsec = -1;
    Elf64_Off dynsym_off = 0;
    Elf64_Xword dynsym_sz = 0;
    int dynsym_strsec = -1;
    if (eh->e_shnum > 0 && eh->e_shoff != 0) {
        const Elf64_Shdr *sh = (const Elf64_Shdr *)(bytes + eh->e_shoff);
        for (int i = 0; i < eh->e_shnum; i++) {
            if (sh[i].sh_type == SHT_DYNAMIC) {
                dyn_off = sh[i].sh_offset;
                dyn_sz = sh[i].sh_size;
                dyn_strsec = (int)sh[i].sh_link;
            } else if (sh[i].sh_type == SHT_DYNSYM) {
                dynsym_off = sh[i].sh_offset;
                dynsym_sz = sh[i].sh_size;
                dynsym_strsec = (int)sh[i].sh_link;
            }
        }
    }

    /* ── DT_NEEDED: conan dependency chain embedded in artifact ── */
    int needs_wayland = 0;
    int needs_pixman = 0;
    if (dyn_off && dyn_sz && dyn_strsec >= 0) {
        const Elf64_Shdr *sh = (const Elf64_Shdr *)(bytes + eh->e_shoff);
        const char *dynstr = (const char *)(bytes + sh[dyn_strsec].sh_offset);
        const Elf64_Dyn *dyn = (const Elf64_Dyn *)(bytes + dyn_off);
        for (size_t d = 0; d < dyn_sz / sizeof(Elf64_Dyn); d++) {
            if (dyn[d].d_tag == DT_NULL) {
                break;
            }
            if (dyn[d].d_tag == DT_NEEDED) {
                const char *name = dynstr + dyn[d].d_un.d_val;
                if (strstr(name, "libwayland-client") != NULL) {
                    needs_wayland = 1;
                }
                if (strstr(name, "libpixman-1") != NULL) {
                    needs_pixman = 1;
                }
            }
        }
    }

    /* ── .dynsym: no undefined glibc-only backtrace symbols ── */
    int undef_backtrace = 0;
    int undef_backtrace_fd = 0;
    if (dynsym_off && dynsym_sz && dynsym_strsec >= 0) {
        const Elf64_Shdr *sh = (const Elf64_Shdr *)(bytes + eh->e_shoff);
        const char *dynstr = (const char *)(bytes + sh[dynsym_strsec].sh_offset);
        const Elf64_Sym *sym = (const Elf64_Sym *)(bytes + dynsym_off);
        for (size_t i = 0; i < dynsym_sz / sizeof(Elf64_Sym); i++) {
            if (sym[i].st_shndx != SHN_UNDEF || sym[i].st_name == 0) {
                continue;
            }
            const char *nm = dynstr + sym[i].st_name;
            if (strcmp(nm, "backtrace") == 0) {
                undef_backtrace = 1;
            }
            if (strcmp(nm, "backtrace_symbols_fd") == 0) {
                undef_backtrace_fd = 1;
            }
        }
    }

    check(has_interp, "dynamically linked (PT_INTERP present)");
    check(has_stack && stack_nx, "non-executable stack (NX)");
    check(has_relro, "RELRO (PT_GNU_RELRO present)");
    check(needs_wayland, "links libwayland-client (Conan dependency chain)");
    check(needs_pixman, "links libpixman-1 (Conan dependency chain)");
    check(!undef_backtrace && !undef_backtrace_fd,
          "no glibc backtrace dependency (OHOS/musl portability guard effective)");

    printf("wayneko OHOS-specific consumer test: %d passed, %d failed\n",
           g_pass, g_fail);
    munmap(map, (size_t)st.st_size);
    return g_fail == 0 ? 0 : 1;
}
