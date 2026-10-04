/*
 * HarmonyOS / OHOS platform-specific test for kea-dhcp4.
 *
 * The upstream gtest suite (src/bin/dhcp4/tests, suite 'kea-dhcp4-tests',
 * 948 cases) verifies the server logic on whichever Linux-like target it is
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
 *   7. DT_NEEDED does not use the GNU naming       -> no "libstdc++"
 *   8. the string-table parse is guarded (DT_STRSZ fits the buffer and the
 *      DT_NEEDED offsets actually resolve) instead of silently truncating:
 *      kea's dynstr is ~156 KB, past a naive 64 KB buffer
 *
 * Only ELF parsing is used, so the test itself is portable but can only pass
 * for an OHOS-built artefact.  Exit code is non-zero on any failed check, so
 * CTest / the Conan test_package reports the regression.
 *
 * Usage: test_ohos_platform <package>/bin/kea-dhcp4
 */
#include <elf.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#define MAX_PHDR 64
#define MAX_DYN 512
#define MAX_NEEDED 64

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

/* Versioned sonames keep the base name as prefix ("libstdc++.so.6"). */
static int has_needed_prefix(char needed[][256], int count, const char *prefix) {
    int i;
    size_t plen = strlen(prefix);
    for (i = 0; i < count; ++i) {
        if (strncmp(needed[i], prefix, plen) == 0) {
            return 1;
        }
    }
    return 0;
}

int main(int argc, char **argv) {
    const char *path;
    int fd, nph, ndyn = 0, nneeded = 0, saw_needed = 0, i;
    Elf64_Ehdr eh;
    Elf64_Phdr ph[MAX_PHDR];
    Elf64_Dyn dyn[MAX_DYN];
    Elf64_Addr dyn_off = 0;
    Elf64_Xword dyn_size = 0;
    unsigned long long strtab_off = 0, strsz = 0, fsize = 0;
    struct stat st;
    char needed[MAX_NEEDED][256];
    /* kea's dynstr is ~156 KB; 64 KB is not enough and silently drops every
     * DT_NEEDED offset beyond it (offsets must be < strsz to be copied).
     * Static: keeps ~256 KiB off the stack (the sibling kea recipes keep this
     * same buffer static for the same reason). */
    static char strtab[262144];

    if (argc != 2) {
        fprintf(stderr, "usage: %s <path-to-kea-dhcp4>\n", argv[0]);
        return 2;
    }
    path = argv[1];

    fd = open(path, O_RDONLY);
    if (fd < 0) {
        perror("open");
        return 2;
    }
    if (fstat(fd, &st) == 0) {
        fsize = (unsigned long long)st.st_size;
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
                if (vaddr_to_off(ph, nph, dyn[i].d_un.d_ptr, &strtab_off) != 0) {
                    fprintf(stderr, "debug: DT_STRTAB VA 0x%llx not in any PT_LOAD\n",
                            (unsigned long long)dyn[i].d_un.d_ptr);
                }
            } else if (dyn[i].d_tag == DT_STRSZ) {
                strsz = dyn[i].d_un.d_val;
            } else if (dyn[i].d_tag == DT_NEEDED) {
                saw_needed = 1;
            }
        }
        /* A string table larger than the buffer (or running past EOF) would
         * be silently truncated - DT_NEEDED offsets are only copied when
         * < strsz, so every entry beyond the cut is dropped.  Fail loudly
         * instead of clamping (the sibling kea recipes guard the same way). */
        check(strsz <= sizeof(strtab), "DT_STRSZ fits the string-table buffer");
        if (strsz <= sizeof(strtab) && strtab_off != 0 && strsz != 0
            && strtab_off + strsz <= fsize
            && read_at(fd, strtab, (size_t)strsz, strtab_off) == 0) {
            for (i = 0; i < ndyn && nneeded < MAX_NEEDED; ++i) {
                if (dyn[i].d_tag == DT_NEEDED && dyn[i].d_un.d_val < strsz) {
                    const char *s = strtab + dyn[i].d_un.d_val;
                    /* bounded copy: the string table is NUL terminated */
                    size_t len = strnlen(s, (size_t)(strsz - dyn[i].d_un.d_val));
                    if (len < sizeof(needed[0])) {
                        memcpy(needed[nneeded], s, len);
                        needed[nneeded][len] = '\0';
                        nneeded++;
                    }
                }
            }
        } else {
            fprintf(stderr,
                    "debug: strtab read skipped (strtab_off=%llu strsz=%llu)\n",
                    (unsigned long long)strtab_off,
                    (unsigned long long)strsz);
        }
        /* DT_NEEDED present but nothing extracted means the string-table
         * resolution failed; that must not pass as a static-artefact skip. */
        check(!(saw_needed && nneeded == 0),
              "DT_NEEDED entries are resolvable through the string table");
        printf("info - DT_NEEDED closure (%d entries)\n", nneeded);
        for (i = 0; i < nneeded; ++i) {
            printf("info -   %s\n", needed[i]);
        }
    }
    close(fd);

    /* libc check: the OHOS build must not drag in glibc; a fully static
     * artefact legitimately has no libc entry at all. */
    if (nneeded == 0 || !(has_needed(needed, nneeded, "libc.so")
                          || has_needed(needed, nneeded, "libc.so.6"))) {
        printf("info - no libc DT_NEEDED entry (static runtime), libc check skipped\n");
    } else {
        check(has_needed(needed, nneeded, "libc.so"),
              "DT_NEEDED links the OHOS musl libc (\"libc.so\")");
    }
    check(!has_needed(needed, nneeded, "libc.so.6"),
          "DT_NEEDED does not use the glibc naming (\"libc.so.6\")");

    /* libc++ check: libc++_shared.so is the OHOS naming; GNU/libc++ upstream
     * namings must not appear.  Static artefacts skip the positive check. */
    if (nneeded == 0 || !(has_needed(needed, nneeded, "libc++_shared.so")
                          || has_needed_prefix(needed, nneeded, "libstdc++")
                          || has_needed_prefix(needed, nneeded, "libc++.so"))) {
        printf("info - no libc++ DT_NEEDED entry (static runtime), libc++ check skipped\n");
    } else {
        check(has_needed(needed, nneeded, "libc++_shared.so"),
              "DT_NEEDED links the OHOS libc++ runtime (\"libc++_shared.so\")");
    }
    check(!has_needed_prefix(needed, nneeded, "libstdc++"),
          "DT_NEEDED does not use the GNU libstdc++ naming (\"libstdc++\")");

    if (failures == 0) {
        printf("kea-dhcp4/3.0.3 OHOS platform check OK\n");
        return 0;
    }
    printf("kea-dhcp4/3.0.3 OHOS platform check FAILED (%d check(s))\n", failures);
    return 1;
}
