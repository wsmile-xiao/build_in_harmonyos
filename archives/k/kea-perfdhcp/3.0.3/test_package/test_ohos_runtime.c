/*
 * HarmonyOS-specific runtime test for kea-perfdhcp.
 *
 * perfdhcp is linked dynamically against ten Kea shared libraries that the
 * package ships under lib/ (libkea-*.so*).  On HarmonyOS the loader has to
 * resolve that closure with musl/bionic-derived semantics (soname symlinks,
 * libc++ runtime, no glibc ld.so.cache), so "does the packaged client actually
 * run" is platform specific and is checked here at run time.
 *
 * Checks
 *   1. the directory of the packaged client exists and is readable
 *   2. every DT_NEEDED entry of bin/perfdhcp that names a Kea library is
 *      shipped inside the package (libkea-*.so* present)
 *   3. at least 10 real libkea-*.so* files are packaged
 *   4. every packaged Kea library loads under the OHOS loader with
 *      dlopen(RTLD_NOW) (each failure prints its dlerror())
 *   5. executing the packaged client ("perfdhcp -v") succeeds under the OHOS
 *      loader and prints the 3.0.3 version string -- i.e. the whole NEEDED
 *      closure of the real process is resolvable at run time
 *
 * Usage: test_ohos_runtime <package>/bin/perfdhcp
 * Exits non-zero on any failed check.
 */
#include <dlfcn.h>
#include <dirent.h>
#include <elf.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

#define EXPECTED_MIN_KEA_LIBS 10
#define MAX_NEEDED 64
#define MAX_PHDR 64
#define MAX_DYN 512
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

/* Collect the DT_NEEDED names of an ELF object. */
static int elf_needed(const char *path, char needed[][256], int max) {
    Elf64_Ehdr eh;
    Elf64_Phdr ph[MAX_PHDR];
    Elf64_Dyn dyn[MAX_DYN];
    Elf64_Addr dyn_off = 0;
    Elf64_Xword dyn_size = 0;
    unsigned long long strtab_off = 0, strsz = 0;
    static char strtab[STRTAB_SIZE];
    int fd, nph, ndyn = 0, nneeded = 0, i;

    fd = open(path, O_RDONLY);
    if (fd < 0) {
        return -1;
    }
    if (read_at(fd, &eh, sizeof(eh), 0) != 0) {
        close(fd);
        return -1;
    }
    nph = eh.e_phnum < MAX_PHDR ? eh.e_phnum : MAX_PHDR;
    for (i = 0; i < nph; ++i) {
        if (read_at(fd, &ph[i], sizeof(Elf64_Phdr),
                    (unsigned long long)eh.e_phoff
                        + (unsigned long long)i * eh.e_phentsize) != 0) {
            close(fd);
            return -1;
        }
        if (ph[i].p_type == PT_DYNAMIC) {
            dyn_off = ph[i].p_offset;
            dyn_size = ph[i].p_filesz;
        }
    }
    if (dyn_off == 0) {
        close(fd);
        return -1;
    }
    size_t n = (size_t)(dyn_size / sizeof(Elf64_Dyn));
    if (n > MAX_DYN) {
        n = MAX_DYN;
    }
    if (read_at(fd, dyn, n * sizeof(Elf64_Dyn), dyn_off) != 0) {
        close(fd);
        return -1;
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
        for (i = 0; i < ndyn && nneeded < max; ++i) {
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
    close(fd);
    return nneeded;
}

static int is_kea_lib(const char *name) {
    return strncmp(name, "libkea-", 7) == 0 && strstr(name, ".so") != NULL;
}

/* <pkg>/bin/perfdhcp -> <pkg> */
static void package_root(const char *exe, char *out, size_t outsz) {
    char buf[4096];
    char *slash;
    snprintf(buf, sizeof(buf), "%s", exe);
    slash = strrchr(buf, '/');          /* strip "perfdhcp" */
    if (slash != NULL) {
        *slash = '\0';
    }
    slash = strrchr(buf, '/');          /* strip "bin" */
    if (slash != NULL) {
        *slash = '\0';
    }
    snprintf(out, outsz, "%s", buf);
}

static int run_version(const char *exe, char *out, size_t outsz) {
    char cmd[8192];
    FILE *f;
    size_t len = 0;
    int status;

    out[0] = '\0';
    snprintf(cmd, sizeof(cmd), "\"%s\" -v 2>/dev/null", exe);
    f = popen(cmd, "r");
    if (f == NULL) {
        return -1;
    }
    len = fread(out, 1, outsz - 1, f);
    out[len] = '\0';
    status = pclose(f);
    return status;
}

int main(int argc, char **argv) {
    char root[4096], libdir[4096];
    char needed[MAX_NEEDED][256];
    const char *exe;
    DIR *dir;
    struct dirent *entry;
    int nneeded, nreal = 0, nloaded = 0, i, missing = 0;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <path-to-perfdhcp>\n", argv[0]);
        return 2;
    }
    exe = argv[1];
    package_root(exe, root, sizeof(root));
    snprintf(libdir, sizeof(libdir), "%s/lib", root);
    printf("info - packaged root: %s\n", root);
    printf("info - packaged Kea runtime lib dir: %s\n", libdir);

    dir = opendir(libdir);
    check(dir != NULL, "packaged lib/ directory is present and readable");
    if (dir == NULL) {
        perror("opendir");
        if (failures != 0) {
            printf("kea-perfdhcp/3.0.3 OHOS runtime check FAILED (%d check(s))\n",
                   failures);
        }
        return 1;
    }

    /* 2. every Kea library the client needs is shipped in the package */
    nneeded = elf_needed(exe, needed, MAX_NEEDED);
    check(nneeded > 0, "bin/perfdhcp has a readable DT_NEEDED closure");
    for (i = 0; i < nneeded; ++i) {
        char full[4096];
        if (!is_kea_lib(needed[i])) {
            continue;
        }
        snprintf(full, sizeof(full), "%s/%s", libdir, needed[i]);
        if (access(full, R_OK) != 0) {
            printf("FAIL - needed Kea library not packaged: %s\n", needed[i]);
            failures++;
            missing++;
        }
    }
    check(missing == 0, "every Kea library named in DT_NEEDED is packaged");

    /* 4. the OHOS loader maps every packaged Kea library */
    rewinddir(dir);
    while ((entry = readdir(dir)) != NULL) {
        char full[4096];
        struct stat st;
        void *handle;

        if (!is_kea_lib(entry->d_name)) {
            continue;
        }
        snprintf(full, sizeof(full), "%s/%s", libdir, entry->d_name);
        if (lstat(full, &st) != 0) {
            continue;
        }
        if (S_ISLNK(st.st_mode)) {
            /* the soname symlinks are covered by loading the real file */
            continue;
        }
        nreal++;
        handle = dlopen(full, RTLD_NOW | RTLD_LOCAL);
        if (handle != NULL) {
            printf("ok   - OHOS loader dlopen(RTLD_NOW): %s\n", entry->d_name);
            nloaded++;
        } else {
            printf("FAIL - OHOS loader dlopen(RTLD_NOW): %s -> %s\n",
                   entry->d_name, dlerror());
            failures++;
        }
    }
    closedir(dir);

    check(nreal >= EXPECTED_MIN_KEA_LIBS,
          "packaged Kea runtime closure present (>= 10 libraries)");
    check(nloaded == nreal,
          "every packaged Kea runtime library loads under the OHOS loader");
    printf("info - Kea runtime libraries: %d found, %d loaded\n", nreal, nloaded);

    /* 5. the packaged client runs under the OHOS loader */
    {
        char out[4096];
        int status = run_version(exe, out, sizeof(out));
        char *nl = strchr(out, '\n');
        if (nl != NULL) {
            *nl = '\0';
        }
        printf("info - \"perfdhcp -v\" output: %s\n", out);
        if (status == -1) {
            printf("FAIL - could not spawn the packaged perfdhcp\n");
            failures++;
        } else if (!WIFEXITED(status) || WEXITSTATUS(status) != 0) {
            printf("FAIL - packaged perfdhcp -v did not exit 0 (status %d)\n",
                   status);
            failures++;
        }
        check(strcmp(out, "3.0.3") == 0,
              "the packaged client runs on the OHOS loader and reports 3.0.3");
    }

    if (failures == 0) {
        printf("kea-perfdhcp/3.0.3 OHOS runtime closure check OK\n");
        return 0;
    }
    printf("kea-perfdhcp/3.0.3 OHOS runtime closure check FAILED (%d check(s))\n",
           failures);
    return 1;
}
