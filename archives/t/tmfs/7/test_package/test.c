/*
 * test_tmfs - consumer-side validation of the packaged tmfs 7 executable.
 *
 * tmfs has no upstream test suite (the 4.5 KB release archive contains no
 * tests/ dir and CMakeLists.txt has no ctest/add_test/enable_testing), so this
 * test drives the packaged binary itself:
 *
 *   T1  `tmfs` with no arguments   -> usage line on stderr, exit code 2
 *   T2  `tmfs <regular file> <mnt>`-> "<file>: is not a directory", exit 1
 *       (the fixture is created in the first writable directory of
 *        $TMPDIR / $HOME / . / /tmp - the OHOS CI worker mounts /tmp read-only,
 *        which made this check fail with EROFS in CI #84208)
 *   T3  ELF contract of the packaged binary: ELF64 / AArch64 / PIE and only
 *       libc.so in DT_NEEDED (FUSE and libc++ are linked statically, so
 *       nothing else can be missing at load time).
 *
 * T1/T2 exercise real branches of src/main.cc and need no /dev/fuse.  When the
 * environment cannot exec the binary (a cross-emulated run root whose libc is
 * not the OHOS one, or an OHOS CI sandbox that refuses exec) the shell reports
 * 126/127 and the test falls back to T3, which is still a real check of the
 * shipped artifact - the same fallback contract as the sshfs 3.7.5-r0
 * test_package.
 *
 * Exit code 0 = every executed check passed.
 */
#include <elf.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

#define EM_AARCH64 183
#define MAX_NEEDED 16

static int checks = 0;
static int failures = 0;
static int exec_blocked = 0;

static void pass(void) { checks++; }

static void failf(const char *fmt, ...) {
    va_list ap;
    va_start(ap, fmt);
    fprintf(stderr, "FAILED: ");
    vfprintf(stderr, fmt, ap);
    fprintf(stderr, "\n");
    va_end(ap);
    failures++;
    checks++;
}

/* Run the binary and capture stdout+stderr. Returns the exit code, -1 when the
 * child could not be started, -2 when it was killed by a signal. */
static int run_capture(const char *path, const char *a1, const char *a2,
                       char *out, size_t outsz) {
    char cmd[3072];
    size_t n = (size_t)snprintf(cmd, sizeof(cmd), "\"%s\"", path);
    if (a1)
        n += (size_t)snprintf(cmd + n, sizeof(cmd) - n, " \"%s\"", a1);
    if (a2)
        n += (size_t)snprintf(cmd + n, sizeof(cmd) - n, " \"%s\"", a2);
    snprintf(cmd + n, sizeof(cmd) - n, " 2>&1");

    FILE *f = popen(cmd, "r");
    if (!f)
        return -1;
    size_t got = fread(out, 1, outsz - 1, f);
    out[got] = '\0';
    int rc = pclose(f);
    if (rc == -1)
        return -1;
    if (WIFEXITED(rc))
        return WEXITSTATUS(rc);
    return -2;
}

/* T1: no arguments -> usage message, exit 2 */
static void check_usage(const char *path) {
    char out[4096];
    int rc = run_capture(path, NULL, NULL, out, sizeof(out));

    if (rc == 126 || rc == 127) {
        printf("[SKIP] cannot execute %s (shell rc=%d); relying on the ELF checks\n",
               path, rc);
        exec_blocked = 1;
        return;
    }
    if (rc != 2) {
        failf("`tmfs` with no args exited %d, expected 2 (output: %s)", rc, out);
        return;
    }
    if (strstr(out, "Usage:") == NULL || strstr(out, "HFS+ mount point") == NULL) {
        failf("usage text not found in output: %s", out);
        return;
    }
    printf("T1 OK: `tmfs` (no args) printed the usage line and exited 2\n");
    pass();
}

/* Create a temporary file in the first writable candidate directory.
 *
 * The OHOS CI worker mounts /tmp read-only - the previous hardcoded
 * "/tmp/tmfs_test_XXXXXX" made this check die with
 *   FAILED: could not create a temporary file: Read-only file system
 * (CI #84208) - so the location is resolved from the environment instead:
 * $TMPDIR, $HOME, the current directory (the test build folder, which conan
 * created and therefore can write) and finally /tmp for plain Linux runs.
 * Returns the fd and stores the path in out; returns -1 when none works and
 * leaves the per-candidate errno trail in tried for the failure message. */
static int make_temp_file(char *out, size_t outsz, char *tried, size_t triedsz) {
    const char *cands[4];
    int ncand = 0;
    const char *env;

    if ((env = getenv("TMPDIR")) != NULL && *env)
        cands[ncand++] = env;
    if ((env = getenv("HOME")) != NULL && *env)
        cands[ncand++] = env;
    cands[ncand++] = ".";
    cands[ncand++] = "/tmp";

    triedsz = triedsz > 0 ? triedsz : 1;
    tried[0] = '\0';
    for (int i = 0; i < ncand; i++) {
        snprintf(out, outsz, "%s/tmfs_test_XXXXXX", cands[i]);
        int fd = mkstemp(out);
        if (fd >= 0) {
            printf("T2: temporary file created in %s\n", cands[i]);
            return fd;
        }
        size_t used = strlen(tried);
        if (used + 64 < triedsz) {
            snprintf(tried + used, triedsz - used, "%s%s (errno=%d)",
                     used ? ", " : "", cands[i], errno);
        }
    }
    return -1;
}

/* T2: hfs_root is a regular file -> "is not a directory", exit 1 */
static void check_not_a_directory(const char *path) {
    char tmp[4000];
    char tried[512];
    char mnt[4096];
    char out[4096];

    int fd = make_temp_file(tmp, sizeof(tmp), tried, sizeof(tried));
    if (fd < 0) {
        failf("could not create a temporary file in any candidate directory: %s",
              tried);
        return;
    }
    close(fd);

    /* argv[2] is only inspected after the hfs_root S_ISDIR check, but keep it
     * next to the fixture in the same writable directory anyway. */
    snprintf(mnt, sizeof(mnt), "%s.mnt", tmp);

    int rc = run_capture(path, tmp, mnt, out, sizeof(out));
    unlink(tmp);

    if (rc == 126 || rc == 127) {
        exec_blocked = 1;
        return;
    }
    if (rc != 1) {
        failf("`tmfs <file> <mnt>` exited %d, expected 1 (output: %s)", rc, out);
        return;
    }
    if (strstr(out, "is not a directory") == NULL) {
        failf("expected the 'is not a directory' diagnostic, got: %s", out);
        return;
    }
    printf("T2 OK: `tmfs <file> <mnt>` reported 'is not a directory' and exited 1\n");
    pass();
}

/* Translate a virtual address into a file offset using the PT_LOAD segments. */
static long vaddr_to_offset(const Elf64_Phdr *phdr, unsigned phnum, unsigned long vaddr) {
    for (unsigned i = 0; i < phnum; i++) {
        if (phdr[i].p_type != PT_LOAD)
            continue;
        if (vaddr >= phdr[i].p_vaddr && vaddr < phdr[i].p_vaddr + phdr[i].p_filesz)
            return (long)(phdr[i].p_offset + (vaddr - phdr[i].p_vaddr));
    }
    return -1;
}

/* T3: structural contract of the packaged ELF. */
static void check_elf(const char *path) {
    FILE *f = fopen(path, "rb");
    if (!f) {
        failf("cannot open the packaged binary %s", path);
        return;
    }

    Elf64_Ehdr h;
    if (fread(&h, 1, sizeof(h), f) != sizeof(h)) {
        fclose(f);
        failf("cannot read the ELF header of %s", path);
        return;
    }
    if (memcmp(h.e_ident, ELFMAG, SELFMAG) != 0 || h.e_ident[EI_CLASS] != ELFCLASS64) {
        fclose(f);
        failf("%s is not an ELF64 file", path);
        return;
    }
    if (h.e_machine != EM_AARCH64) {
        unsigned m = (unsigned)h.e_machine;
        fclose(f);
        failf("e_machine=%u, expected aarch64 (%d)", m, EM_AARCH64);
        return;
    }
    if (h.e_type != ET_DYN) {
        unsigned t = (unsigned)h.e_type;
        fclose(f);
        failf("e_type=%u, expected ET_DYN (PIE executable)", t);
        return;
    }

    Elf64_Phdr *phdr = NULL;
    if (h.e_phentsize != sizeof(Elf64_Phdr) || h.e_phnum == 0) {
        fclose(f);
        failf("unexpected program header layout (phentsize=%u phnum=%u)",
              (unsigned)h.e_phentsize, (unsigned)h.e_phnum);
        return;
    }
    phdr = calloc(h.e_phnum, sizeof(Elf64_Phdr));
    if (!phdr) {
        fclose(f);
        failf("out of memory reading the program headers");
        return;
    }
    if (fseek(f, (long)h.e_phoff, SEEK_SET) != 0 ||
        fread(phdr, sizeof(Elf64_Phdr), h.e_phnum, f) != h.e_phnum) {
        free(phdr);
        fclose(f);
        failf("cannot read the program headers of %s", path);
        return;
    }

    /* DT_NEEDED holds offsets *into* the string table, whose address is given
     * by DT_STRTAB, so the two have to be resolved together. */
    char needed[MAX_NEEDED][256];
    int nneeded = 0;
    int have_dynamic = 0;
    unsigned long strtab_vaddr = 0;
    int have_strtab = 0;

    for (unsigned i = 0; i < h.e_phnum; i++) {
        if (phdr[i].p_type != PT_DYNAMIC)
            continue;
        have_dynamic = 1;
        long dyn = vaddr_to_offset(phdr, h.e_phnum, phdr[i].p_vaddr);
        if (dyn < 0)
            break;

        Elf64_Dyn entries[512];
        int n = 0;
        for (; n < 512; n++) {
            if (fseek(f, dyn + (long)n * (long)sizeof(Elf64_Dyn), SEEK_SET) != 0)
                break;
            if (fread(&entries[n], sizeof(Elf64_Dyn), 1, f) != 1)
                break;
            if (entries[n].d_tag == DT_NULL)
                break;
            if (entries[n].d_tag == DT_STRTAB) {
                strtab_vaddr = (unsigned long)entries[n].d_un.d_val;
                have_strtab = 1;
            }
        }
        if (!have_strtab)
            break;
        for (int k = 0; k < n && nneeded < MAX_NEEDED; k++) {
            if (entries[k].d_tag != DT_NEEDED)
                continue;
            long soff = vaddr_to_offset(phdr, h.e_phnum,
                                        strtab_vaddr +
                                            (unsigned long)entries[k].d_un.d_val);
            if (soff < 0)
                continue;
            if (fseek(f, soff, SEEK_SET) == 0 &&
                fread(needed[nneeded], 1, sizeof(needed[0]) - 1, f) > 0) {
                needed[nneeded][sizeof(needed[0]) - 1] = '\0';
                if (needed[nneeded][0] != '\0')
                    nneeded++;
            }
        }
        break;
    }
    long fsize = (fseek(f, 0, SEEK_END) == 0) ? ftell(f) : -1;
    fclose(f);
    free(phdr);

    if (!have_dynamic) {
        failf("%s has no PT_DYNAMIC segment", path);
        return;
    }

    printf("T3 OK: ELF64 AArch64 PIE, %ld bytes, DT_NEEDED:", fsize);
    for (int i = 0; i < nneeded; i++)
        printf(" %s", needed[i]);
    printf("\n");
    pass();

    if (nneeded == 0) {
        failf("no DT_NEEDED entry found in %s", path);
        return;
    }
    for (int i = 0; i < nneeded; i++) {
        if (strcmp(needed[i], "libc.so") != 0) {
            failf("unexpected DT_NEEDED entry: %s (only libc.so is expected; "
                  "FUSE is linked statically)", needed[i]);
            return;
        }
    }
    printf("T3b OK: only libc.so is needed dynamically (FUSE linked statically)\n");
    pass();
}

int main(int argc, char *argv[]) {
    const char *tmfs_bin = (argc > 1) ? argv[1] : "tmfs";

    check_usage(tmfs_bin);
    check_not_a_directory(tmfs_bin);
    check_elf(tmfs_bin);

    printf("test tmfs 7: %d checks, %d failures%s\n", checks, failures,
           exec_blocked ? " (behaviour checks skipped: exec unavailable)" : "");
    return failures ? 1 : 0;
}
