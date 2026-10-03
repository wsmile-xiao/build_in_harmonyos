/*
 * HarmonyOS-specific platform test for spice 0.16.0 (libspice-server).
 *
 * 上游 meson 套件校验库在任意 Linux 目标上的功能逻辑；本测试校验打包产物
 * 携带的是 OHOS aarch64 平台 ABI 特征（而非通用 glibc/Linux 特征），且 OHOS
 * 加载器可以实际映射。
 *
 * Checks
 *   1. ELF64 executable header (ELFCLASS64)
 *   2. e_machine == EM_AARCH64 (OHOS PC target machine)
 *   3. PT_DYNAMIC segment present
 *   4. DT_NEEDED links against the OHOS musl libc  -> "libc.so"
 *   5. DT_NEEDED does not use the glibc naming     -> no "libc.so.6"
 *   6. DT_NEEDED links against the OHOS libc++     -> "libc++_shared.so"
 *   7. DT_NEEDED links the Conan runtime closure   -> "libglib-2.0.so.0"
 *   8. dlopen(RTLD_NOW|RTLD_LOCAL) succeeds on the OHOS loader
 *
 * 仅用 ELF 解析与 POSIX 调用，测试本身可移植，但只可能对 OHOS 产物通过。
 * 每个用例输出 "TEST PASS - ..." / "TEST FAIL - ..."，结尾输出
 * "TEST SUMMARY: N/N passed"；任一失败进程退出码 1。
 *
 * Usage: test_ohos_platform <path-to-libspice-server.so>
 */
#include <dlfcn.h>
#include <elf.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#define MAX_PHDR 64
#define MAX_NEEDED 64

static int tests_run = 0;
static int tests_failed = 0;

static void check(int cond, const char *what)
{
    tests_run++;
    if (cond) {
        printf("TEST PASS - %s\n", what);
    } else {
        printf("TEST FAIL - %s\n", what);
        tests_failed++;
    }
    fflush(stdout);
}

static int read_at(int fd, void *buf, size_t n, unsigned long long off)
{
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
                        unsigned long long *off)
{
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

static int has_needed(char needed[][256], int count, const char *name)
{
    int i;
    for (i = 0; i < count; ++i) {
        if (strcmp(needed[i], name) == 0) {
            return 1;
        }
    }
    return 0;
}

int main(int argc, char **argv)
{
    const char *path;
    int fd, nph, ndyn = 0, nneeded = 0, i;
    Elf64_Ehdr eh;
    Elf64_Phdr ph[MAX_PHDR];
    Elf64_Dyn dyn[512];
    Elf64_Addr dyn_off = 0;
    Elf64_Xword dyn_size = 0;
    unsigned long long strtab_off = 0, strsz = 0;
    char strtab[65536];
    static char needed[MAX_NEEDED][256];
    void *handle;

    if (argc != 2) {
        fprintf(stderr, "usage: %s <path-to-libspice-server.so>\n", argv[0]);
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
        if (n > sizeof(dyn) / sizeof(dyn[0])) {
            n = sizeof(dyn) / sizeof(dyn[0]);
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
        if (strsz > sizeof(strtab)) {
            strsz = sizeof(strtab);
        }
        if (strtab_off != 0 && strsz != 0
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
        }
        close(fd);
        printf("info - DT_NEEDED closure (%d entries)\n", nneeded);
        for (i = 0; i < nneeded; ++i) {
            printf("info -   %s\n", needed[i]);
        }
    } else {
        close(fd);
    }

    check(has_needed(needed, nneeded, "libc.so"),
          "DT_NEEDED links the OHOS musl libc (\"libc.so\")");
    check(!has_needed(needed, nneeded, "libc.so.6"),
          "DT_NEEDED does not use the glibc naming (\"libc.so.6\")");
    check(has_needed(needed, nneeded, "libc++_shared.so"),
          "DT_NEEDED links the OHOS libc++ runtime (\"libc++_shared.so\")");
    check(has_needed(needed, nneeded, "libglib-2.0.so.0"),
          "DT_NEEDED links the Conan runtime closure (\"libglib-2.0.so.0\")");

    handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
    check(handle != NULL, "OHOS loader dlopen(RTLD_NOW) resolves libspice-server");
    if (handle != NULL) {
        dlclose(handle);
    } else {
        fprintf(stderr, "dlopen(%s) failed: %s\n", path, dlerror());
    }

    printf("TEST SUMMARY: %d/%d passed\n", tests_run - tests_failed, tests_run);
    return tests_failed == 0 ? 0 : 1;
}
