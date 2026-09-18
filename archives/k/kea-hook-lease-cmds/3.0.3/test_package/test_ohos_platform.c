/*
 * HarmonyOS / OHOS platform-specific test for kea-hook-lease-cmds.
 *
 * The two upstream gtest suites (dhcp-lease-cmds-lib-tests,
 * dhcp-lease-cmds-libloadtests) verify the plug-in logic on whichever Linux-like
 * target it is built for; this test is the HarmonyOS-specific one: it verifies
 * that the *packaged* artefact carries the OHOS aarch64 platform ABI signature
 * instead of a generic glibc/Linux one, and that the OHOS loader can actually
 * map it.
 *
 * Checks
 *   1. ELF64 executable header (ELFCLASS64)
 *   2. e_machine == EM_AARCH64 (OHOS PC target machine)
 *   3. PT_DYNAMIC segment present, its string table readable from the file
 *   4. DT_NEEDED links against the OHOS musl libc  -> "libc.so"
 *   5. DT_NEEDED does not use the glibc naming     -> no "libc.so.6"
 *   6. DT_NEEDED links against the OHOS libc++     -> "libc++_shared.so"
 *   7. dlopen(RTLD_NOW|RTLD_LOCAL) succeeds, i.e. the OHOS loader resolves
 *      the plug-in and the 20 Kea runtime libraries it depends on
 *
 * Only ELF parsing and POSIX calls are used, so the test itself is portable
 * but can only pass for an OHOS-built artefact.  Exit code is non-zero on any
 * failed check, so CTest / the Conan test_package reports the regression.
 */
#include <dlfcn.h>
#include <elf.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#define MAX_PHDR 64
#define MAX_NEEDED 64
#define MAX_DYNENT 1024
/* Sanity bound for the dynamic string table (the Kea hook needs ~85 KiB). */
#define MAX_STRTAB (16u * 1024u * 1024u)

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
    unsigned long long fsize = 0;
    Elf64_Ehdr eh;
    Elf64_Phdr ph[MAX_PHDR];
    Elf64_Dyn dyn[MAX_DYNENT];
    Elf64_Addr dyn_off = 0;
    Elf64_Xword dyn_size = 0;
    unsigned long long strtab_off = 0, strsz = 0;
    char *strtab = NULL;
    int strtab_ok = 0;
    char needed[MAX_NEEDED][256];
    void *handle;

    for (i = 0; i < MAX_NEEDED; ++i) {
        needed[i][0] = '\0';
    }

    if (argc != 2) {
        fprintf(stderr, "usage: %s <path-to-libdhcp_lease_cmds.so>\n", argv[0]);
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
    {
        struct stat st;
        if (fstat(fd, &st) == 0) {
            fsize = (unsigned long long)st.st_size;
        }
    }

    check(memcmp(eh.e_ident, ELFMAG, SELFMAG) == 0, "ELF magic present");
    check(eh.e_ident[EI_CLASS] == ELFCLASS64, "ELFCLASS64 (64-bit OHOS PC target)");
    check(eh.e_machine == EM_AARCH64, "e_machine == EM_AARCH64 (OHOS aarch64)");

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
        if (n > MAX_DYNENT) {
            n = MAX_DYNENT;
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
    }

    /* The DT_NEEDED names live in the dynamic string table.  For the Kea hook
     * it is ~85 KiB, so it is allocated instead of being put on the stack. */
    if (strtab_off != 0 && strsz != 0 && strsz <= MAX_STRTAB
        && strtab_off + strsz <= fsize) {
        strtab = (char *)malloc((size_t)strsz);
        if (strtab != NULL
            && read_at(fd, strtab, (size_t)strsz, strtab_off) == 0) {
            strtab_ok = 1;
        }
    }
    check(strtab_ok,
          "dynamic string table (DT_STRTAB/DT_STRSZ) read from the file");

    if (strtab_ok) {
        for (i = 0; i < ndyn && nneeded < MAX_NEEDED; ++i) {
            unsigned long long off;
            const char *s;
            size_t len;
            if (dyn[i].d_tag != DT_NEEDED) {
                continue;
            }
            off = dyn[i].d_un.d_val;
            if (off >= strsz) {
                continue;
            }
            s = strtab + off;
            /* bounded copy: the string table is NUL terminated */
            len = strnlen(s, (size_t)(strsz - off));
            if (len > 0 && len < sizeof(needed[0])) {
                memcpy(needed[nneeded], s, len);
                needed[nneeded][len] = '\0';
                nneeded++;
            }
        }
    }
    free(strtab);
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

    handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    check(handle != NULL, "OHOS loader dlopen(RTLD_NOW) resolves the plug-in");
    if (handle != NULL) {
        dlclose(handle);
    } else {
        fprintf(stderr, "dlopen(%s) failed: %s\n", path, dlerror());
    }

    if (failures == 0) {
        printf("kea-hook-lease-cmds/3.0.3 OHOS platform check OK\n");
        return 0;
    }
    printf("kea-hook-lease-cmds/3.0.3 OHOS platform check FAILED (%d check(s))\n",
           failures);
    return 1;
}
