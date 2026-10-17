/*
 * HarmonyOS / OHOS platform-specific test for kea-perfdhcp.
 *
 * The upstream gtest suite (src/bin/perfdhcp/tests, suite 'perfdhcp-tests',
 * 140 cases) verifies the client logic on whichever Linux-like target it is
 * built for.  This test is the HarmonyOS-specific one: it verifies that the
 * *packaged* executable carries the OHOS aarch64 platform ABI signature
 * instead of a generic glibc/Linux one.
 *
 * Checks
 *   1. ELF64 executable header (ELFCLASS64)
 *   2. e_machine == EM_AARCH64 (OHOS PC target machine)
 *   3. e_type == ET_DYN, i.e. the PIE build OHOS requires for executables
 *   4. DT_NEEDED links against the OHOS musl libc  -> "libc.so"
 *   5. DT_NEEDED does not use the glibc naming     -> no "libc.so.6"
 *   6. DT_NEEDED links against the OHOS libc++     -> "libc++_shared.so"
 *
 * Only ELF parsing is used, so the test itself is portable but can only pass
 * for an OHOS-built artefact.  Exit code is non-zero on any failed check, so
 * CTest / the Conan test_package reports the regression.
 *
 * Usage: test_ohos_platform <package>/bin/perfdhcp
 */
#include <elf.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <unistd.h>

#define MAX_PHDR 64
#define MAX_DYN 512
#define MAX_NEEDED 64
#define STRTAB_SIZE 65536

static int failures = 0;

static void check(int cond, const char *what) {
    if (cond) {
        printf("ok   - %s\n", what);
    } else {
        printf("FAIL - %s\n", what);
        failures++;
    }
    fflush(stdout);
}

static int read_at(int fd, void *buf, size_t n, unsigned long long off) {
    unsigned char *p = (unsigned char *)buf;
    size_t done = 0;
    while (done < n) {
        ssize_t r = pread(fd, p + done, n - done, (off_t)(off + done));
        if (r <= 0) {
            return -1;
        }
        done += (size_t)r;
    }
    return 0;
}

/* Map a virtual address to a file offset through the PT_LOAD headers. */
static int vaddr_to_off(const Elf64_Phdr *ph, int nph, Elf64_Addr va,
                        unsigned long long *off) {
    int i;
    for (i = 0; i < nph; ++i) {
        if (ph[i].p_type != PT_LOAD) {
            continue;
        }
        if (va >= ph[i].p_vaddr && va < ph[i].p_vaddr + ph[i].p_memsz) {
            *off = (unsigned long long)(ph[i].p_offset + (va - ph[i].p_vaddr));
            return 0;
        }
    }
    return -1;
}

static int has_needed(char needed[][256], int count, const char *name) {
    int i;
    for (i = 0; i < count; ++i) {
        if (strcmp(needed[i], name) == 0) {
            return 1;
        }
    }
    return 0;
}

int main(int argc, char **argv) {
    const char *path;
    int fd, nph, ndyn = 0, nneeded = 0, i;
    Elf64_Ehdr eh;
    Elf64_Phdr ph[MAX_PHDR];
    Elf64_Dyn dyn[MAX_DYN];
    Elf64_Addr dyn_off = 0;
    Elf64_Xword dyn_size = 0;
    unsigned long long strtab_off = 0, strsz = 0;
    static char strtab[STRTAB_SIZE];
    static char needed[MAX_NEEDED][256];

    if (argc != 2) {
        fprintf(stderr, "usage: %s <path-to-perfdhcp>\n", argv[0]);
        return 2;
    }
    path = argv[1];

    fd = open(path, O_RDONLY);
    if (fd < 0) {
        perror("open");
        return 2;
    }
    if (read_at(fd, &eh, sizeof(eh), 0) != 0) {
        fprintf(stderr, "cannot read ELF header of %s\n", path);
        close(fd);
        return 2;
    }

    check(memcmp(eh.e_ident, ELFMAG, SELFMAG) == 0, "ELF magic present");
    check(eh.e_ident[EI_CLASS] == ELFCLASS64, "ELFCLASS64 (64-bit OHOS PC target)");
    check(eh.e_machine == EM_AARCH64, "e_machine == EM_AARCH64 (OHOS aarch64)");
    check(eh.e_type == ET_DYN, "e_type == ET_DYN (PIE executable, as OHOS requires)");

    nph = eh.e_phnum < MAX_PHDR ? eh.e_phnum : MAX_PHDR;
    for (i = 0; i < nph; ++i) {
        if (read_at(fd, &ph[i], sizeof(Elf64_Phdr),
                    (unsigned long long)eh.e_phoff
                        + (unsigned long long)i * eh.e_phentsize) != 0) {
            fprintf(stderr, "cannot read program header %d\n", i);
            close(fd);
            return 2;
        }
        if (ph[i].p_type == PT_DYNAMIC) {
            dyn_off = ph[i].p_offset;
            dyn_size = ph[i].p_filesz;
        }
    }
    check(dyn_off != 0, "PT_DYNAMIC segment present");

    if (dyn_off != 0) {
        size_t n = (size_t)(dyn_size / sizeof(Elf64_Dyn));
        if (n > MAX_DYN) {
            n = MAX_DYN;
        }
        if (read_at(fd, dyn, n * sizeof(Elf64_Dyn), dyn_off) != 0) {
            fprintf(stderr, "cannot read dynamic section\n");
            close(fd);
            return 2;
        }
        ndyn = (int)n;
        for (i = 0; i < ndyn; ++i) {
            if (dyn[i].d_tag == DT_STRTAB) {
                (void)vaddr_to_off(ph, nph, dyn[i].d_un.d_ptr, &strtab_off);
            } else if (dyn[i].d_tag == DT_STRSZ) {
                strsz = dyn[i].d_un.d_val;
            }
        }
        if (strsz > STRTAB_SIZE) {
            strsz = STRTAB_SIZE;
        }
        if (strtab_off != 0 && strsz != 0
            && read_at(fd, strtab, (size_t)strsz, strtab_off) == 0) {
            for (i = 0; i < ndyn && nneeded < MAX_NEEDED; ++i) {
                if (dyn[i].d_tag == DT_NEEDED && dyn[i].d_un.d_val < strsz) {
                    const char *s = strtab + dyn[i].d_un.d_val;
                    size_t len = strnlen(s, (size_t)(strsz - dyn[i].d_un.d_val));
                    if (len < sizeof(needed[0])) {
                        memcpy(needed[nneeded], s, len);
                        needed[nneeded][len] = '\0';
                        nneeded++;
                    }
                }
            }
        }
    }
    close(fd);

    printf("info - DT_NEEDED closure (%d entries)\n", nneeded);
    for (i = 0; i < nneeded; ++i) {
        printf("info -   %s\n", needed[i]);
    }

    check(has_needed(needed, nneeded, "libc.so"),
          "DT_NEEDED links the OHOS musl libc (\"libc.so\")");
    check(!has_needed(needed, nneeded, "libc.so.6"),
          "DT_NEEDED does not use the glibc naming (\"libc.so.6\")");
    check(has_needed(needed, nneeded, "libc++_shared.so"),
          "DT_NEEDED links the OHOS libc++ runtime (\"libc++_shared.so\")");

    if (failures == 0) {
        printf("kea-perfdhcp/3.0.3 OHOS platform check OK\n");
        return 0;
    }
    printf("kea-perfdhcp/3.0.3 OHOS platform check FAILED (%d check(s))\n", failures);
    return 1;
}
