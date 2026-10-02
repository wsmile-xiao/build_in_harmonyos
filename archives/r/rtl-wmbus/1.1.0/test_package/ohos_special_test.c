/* ohos_special_test.c — HarmonyOS-specific verification for rtl-wmbus 1.1.0.
 *
 * A cross-compiled binary that merely *runs* under emulation does not prove the
 * port is real. This test asserts the packaged executable is genuinely an OHOS
 * aarch64 (musl) build by parsing its ELF image, and then exercises the
 * POSIX-only code paths that upstream compiles out on Windows
 * (rtl_wmbus.c guards `WINDOWS_BUILD` around signal/alarm and socket support).
 *
 * The ABI checks are gated on TARGET_IS_OHOS_AARCH64, which the test_package
 * conanfile derives from `settings.os`/`settings.arch`. The recipe accepts
 * os=Linux as well, and on a native non-OHOS build the OHOS-specific
 * expectations (EM_AARCH64, the musl loader) would be wrong rather than
 * revealing a defect — so they are reported as skipped instead of failed.
 * CI always builds os=OHOS/arch=armv8, so there they run in full.
 *
 * Checks (platform-neutral, always run)
 *   ELF   1. ELF64 little-endian image with a valid magic
 *   ELF   2. e_type == ET_DYN (3)                -> position independent
 *   ELF   3. PT_GNU_STACK is non-executable      -> NX stack
 *   ELF   4. dynamic section parsed (DT_NEEDED read back from the image)
 *   POSIX 5. `-f` exits non-zero when stdin stalls (alarm(5) + SIGALRM handler,
 *          compiled in only for non-Windows builds)
 *   POSIX 6. `-f` gave up on its own (elapsed bound, see comment at the check)
 *   POSIX 7. `-p X` rejects an invalid mode argument with status 1 (getopt)
 *   POSIX 8. `-s` combined S1+T1/C1 mode is accepted (status 0)
 *
 * Checks (only when TARGET_IS_OHOS_AARCH64; 13 total on an OHOS build)
 *   ELF   9. e_machine == EM_AARCH64 (183)       -> targets OHOS aarch64
 *   ELF  10. binary has a PT_INTERP              -> dynamically linked, not static
 *   ELF  11. PT_INTERP is the aarch64 musl loader under /lib (layout only)
 *   ELF  12. DT_NEEDED has no glibc-only soname   -> linked against musl
 *   ELF  13. DT_NEEDED carries the musl libc soname
 *
 * Note on PT_INTERP: it is a layout/loader sanity check, NOT the musl-vs-glibc
 * discriminator — glibc's aarch64 loader is also /lib/ld-linux-aarch64.so.1.
 * The discrimination is carried by the exact DT_NEEDED soname assertions below
 * (OHOS links libc.so, glibc links libc.so.6). Both musl loader spellings are
 * accepted because they genuinely differ per toolchain: the OHOS CI worker's NDK
 * toolchain emits /lib/ld-musl-aarch64.so.1, a stock musl/clang cross build
 * emits /lib/ld-linux-aarch64.so.1.
 */
#define _GNU_SOURCE
#include <elf.h>
#include <errno.h>
#include <fcntl.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#ifndef TARGET_IS_OHOS_AARCH64
#define TARGET_IS_OHOS_AARCH64 1
#endif

static int failures;
static int checks;

static void ok(int cond, const char *fmt, ...)
{
    va_list ap;
    checks++;
    va_start(ap, fmt);
    if (cond) {
        printf("  [ok]   ");
    } else {
        printf("  [FAIL] ");
        failures++;
    }
    vprintf(fmt, ap);
    printf("\n");
    va_end(ap);
    fflush(stdout);
}

static void note(const char *fmt, ...)
{
    va_list ap;
    printf("  [skip] ");
    va_start(ap, fmt);
    vprintf(fmt, ap);
    printf("\n");
    va_end(ap);
    fflush(stdout);
}

static const char *rtl_bin(void)
{
    const char *e = getenv("RTL_WMBUS_BIN");
    return (e && *e) ? e : "rtl_wmbus";
}

/* Resolve the packaged executable through PATH (VirtualRunEnv). */
static int resolve_bin(char *out, size_t cap)
{
    const char *e = getenv("RTL_WMBUS_BIN");
    if (e && *e) {
        snprintf(out, cap, "%s", e);
        return access(out, R_OK) == 0;
    }
    const char *path = getenv("PATH");
    if (!path || !*path)
        return 0;
    char *dup = strdup(path);
    if (!dup)
        return 0;
    int found = 0;
    for (char *dir = strtok(dup, ":"); dir && !found; dir = strtok(NULL, ":")) {
        snprintf(out, cap, "%s/rtl_wmbus", *dir ? dir : ".");
        if (access(out, R_OK) == 0)
            found = 1;
    }
    free(dup);
    return found;
}

/* Read the whole ELF image. Returns NULL on failure. */
static unsigned char *load_image(const char *path, long *size_out)
{
    FILE *f = fopen(path, "rb");
    unsigned char *img = NULL;
    if (!f)
        return NULL;
    if (fseek(f, 0, SEEK_END) == 0 && (size_t)(*size_out = ftell(f)) > 0) {
        rewind(f);
        img = malloc((size_t)*size_out);
        if (img && fread(img, 1, (size_t)*size_out, f) != (size_t)*size_out) {
            free(img);
            img = NULL;
        }
    }
    fclose(f);
    return img;
}

/* Collect DT_NEEDED sonames from an ELF64 little-endian image. -1 on failure. */
static int needed_sonames(const unsigned char *img, long sz, char names[][128], int max)
{
    const Elf64_Ehdr *eh;
    const Elf64_Phdr *ph;
    const Elf64_Dyn *dyn;
    uint64_t dyn_off = 0, dyn_sz = 0, strtab_vaddr = 0, strtab_sz = 0, str_off = 0;
    int have_dyn = 0, count = 0;

    /* Never dereference the header before the image is known to be big enough. */
    if (sz < (long)sizeof(Elf64_Ehdr))
        return -1;
    eh = (const Elf64_Ehdr *)img;
    if (memcmp(img, ELFMAG, SELFMAG) != 0 ||
        img[EI_CLASS] != ELFCLASS64 || img[EI_DATA] != ELFDATA2LSB)
        return -1;
    if (eh->e_phentsize < sizeof(Elf64_Phdr) ||
        (size_t)eh->e_phoff + (size_t)eh->e_phnum * eh->e_phentsize > (size_t)sz)
        return -1;

    ph = (const Elf64_Phdr *)(img + eh->e_phoff);
    for (int i = 0; i < eh->e_phnum; i++) {
        if (ph[i].p_type == PT_DYNAMIC &&
            ph[i].p_offset + ph[i].p_filesz <= (uint64_t)sz) {
            dyn_off = ph[i].p_offset;
            dyn_sz = ph[i].p_filesz;
            have_dyn = 1;
        }
    }
    if (!have_dyn)
        return -1;

    dyn = (const Elf64_Dyn *)(img + dyn_off);
    for (uint64_t o = 0; o + sizeof(Elf64_Dyn) <= dyn_sz; o += sizeof(Elf64_Dyn)) {
        Elf64_Sxword tag = dyn[o / sizeof(Elf64_Dyn)].d_tag;
        Elf64_Xword val = dyn[o / sizeof(Elf64_Dyn)].d_un.d_val;
        if (tag == DT_NULL)
            break;
        if (tag == DT_STRTAB)
            strtab_vaddr = val;
        else if (tag == DT_STRSZ)
            strtab_sz = val;
    }
    if (!strtab_vaddr || !strtab_sz)
        return -1;

    /* Translate the dynamic string table vaddr into a file offset. */
    for (int i = 0; i < eh->e_phnum; i++) {
        if (ph[i].p_type == PT_LOAD &&
            strtab_vaddr >= ph[i].p_vaddr &&
            strtab_vaddr < ph[i].p_vaddr + ph[i].p_filesz) {
            str_off = ph[i].p_offset + (strtab_vaddr - ph[i].p_vaddr);
            break;
        }
    }
    if (!str_off || str_off >= (uint64_t)sz)
        return -1;

    for (uint64_t o = 0; o + sizeof(Elf64_Dyn) <= dyn_sz && count < max;
         o += sizeof(Elf64_Dyn)) {
        if (dyn[o / sizeof(Elf64_Dyn)].d_tag == DT_NEEDED) {
            uint64_t so = str_off + dyn[o / sizeof(Elf64_Dyn)].d_un.d_val;
            if (so >= (uint64_t)sz)
                continue;
            snprintf(names[count], sizeof names[0], "%s", (const char *)(img + so));
            count++;
        }
    }
    return count;
}

/* Exact soname comparison: "libc.so" must not match glibc's "libc.so.6". */
static int has_soname(char names[][128], int n, const char *want)
{
    for (int i = 0; i < n; i++)
        if (strcmp(names[i], want) == 0)
            return 1;
    return 0;
}

static int is_glibc_soname(const char *s)
{
    static const char *glibc[] = {
        "libc.so.6", "libm.so.6", "libpthread.so.0", "libdl.so.2",
        "librt.so.1", "libgcc_s.so.1", "libstdc++.so.6", NULL
    };
    for (int i = 0; glibc[i]; i++)
        if (strcmp(s, glibc[i]) == 0)
            return 1;
    return 0;
}

int main(void)
{
    char binpath[4096];
    long sz = 0;
    unsigned char *img;

    printf("rtl-wmbus HarmonyOS-specific verification (target: %s%s)\n",
           rtl_bin(), TARGET_IS_OHOS_AARCH64 ? "" : ", non-OHOS build — ABI checks skipped");

    if (!resolve_bin(binpath, sizeof binpath)) {
        ok(0, "packaged rtl_wmbus is resolvable through PATH");
        printf("\n%d checks, %d failure(s)\n", checks, failures);
        return 1;
    }

    img = load_image(binpath, &sz);
    if (!img || sz < (long)sizeof(Elf64_Ehdr)) {
        ok(0, "packaged rtl_wmbus is a readable ELF image of at least %zu bytes",
           sizeof(Elf64_Ehdr));
        free(img);
        printf("\n%d checks, %d failure(s)\n", checks, failures);
        return 1;
    }

    /* ── ELF header ──────────────────────────────────────────────── */
    {
        const Elf64_Ehdr *eh = (const Elf64_Ehdr *)img;
        ok(memcmp(img, ELFMAG, SELFMAG) == 0 &&
           img[EI_CLASS] == ELFCLASS64 && img[EI_DATA] == ELFDATA2LSB,
           "ELF64 little-endian image with a valid magic");
        ok(eh->e_type == ET_DYN,
           "e_type is ET_DYN / position independent (got %u)", eh->e_type);
    }

    /* ── PT_INTERP + PT_GNU_STACK ────────────────────────────────── */
    {
        const Elf64_Ehdr *eh = (const Elf64_Ehdr *)img;
        const Elf64_Phdr *ph;
        int has_interp = 0, interp_aarch64 = 0, nx_stack = 0;
        char interp[128] = "";

        /* Bounds-check the program header table before indexing it, so a
         * truncated or corrupt image cannot make us read past the buffer. */
        if ((size_t)eh->e_phoff + (size_t)eh->e_phnum * eh->e_phentsize > (size_t)sz ||
            eh->e_phentsize < sizeof(Elf64_Phdr)) {
            ok(0, "program header table lies inside the image");
        } else {
            ph = (const Elf64_Phdr *)(img + eh->e_phoff);
            for (int i = 0; i < eh->e_phnum; i++) {
                if (ph[i].p_type == PT_INTERP && ph[i].p_filesz > 1 &&
                    ph[i].p_offset + ph[i].p_filesz <= (uint64_t)sz) {
                    size_t n = ph[i].p_filesz < sizeof interp - 1
                                   ? ph[i].p_filesz : sizeof interp - 1;
                    memcpy(interp, img + ph[i].p_offset, n);
                    interp[n] = '\0';
                    has_interp = 1;
                    /* Layout check only: musl-vs-glibc is proven by the exact
                     * DT_NEEDED soname assertions below, because glibc's aarch64
                     * loader is also /lib/ld-linux-aarch64.so.1.
                     * Both musl loader names must be accepted — the OHOS CI
                     * worker's NDK toolchain emits /lib/ld-musl-aarch64.so.1
                     * while a stock musl/clang cross build emits
                     * /lib/ld-linux-aarch64.so.1. */
                    interp_aarch64 = strncmp(interp, "/lib/", 5) == 0 &&
                                     strstr(interp, "aarch64") != NULL &&
                                     (strstr(interp, "ld-musl") != NULL ||
                                      strstr(interp, "ld-linux-aarch64") != NULL);
                } else if (ph[i].p_type == PT_GNU_STACK) {
                    nx_stack = !(ph[i].p_flags & PF_X);
                }
            }
            ok(nx_stack, "PT_GNU_STACK is non-executable (NX stack enabled)");

            if (TARGET_IS_OHOS_AARCH64) {
                ok(eh->e_machine == EM_AARCH64,
                   "e_machine is EM_AARCH64 (got %u, want %d)", eh->e_machine, EM_AARCH64);
                ok(has_interp, "binary has a PT_INTERP (dynamically linked against OHOS)");
                ok(interp_aarch64,
                   "PT_INTERP is the aarch64 musl loader under /lib (got \"%s\")",
                   has_interp ? interp : "none");
            } else {
                note("OHOS ABI expectations not applicable to this build "
                     "(e_machine=%u, PT_INTERP=\"%s\")",
                     eh->e_machine, has_interp ? interp : "none");
            }
        }
    }

    /* ── DT_NEEDED ───────────────────────────────────────────────── */
    {
        char names[16][128];
        int n = needed_sonames(img, sz, names, 16);
        int glibc = 0;
        ok(n >= 0, "dynamic section parsed (DT_NEEDED entries: %d)", n);
        for (int i = 0; i < n; i++) {
            printf("         NEEDED: %s\n", names[i]);
            if (is_glibc_soname(names[i]))
                glibc = 1;
        }
        if (TARGET_IS_OHOS_AARCH64) {
            ok(!glibc, "no glibc-only soname is linked (OHOS uses musl)");
            ok(has_soname(names, n, "libc.so") || has_soname(names, n, "libm.so"),
               "links the OHOS musl C library (exact soname libc.so / libm.so)");
        } else {
            note("musl soname expectations not applicable to this build");
        }
    }

    free(img);

    /* ── POSIX-only runtime paths ────────────────────────────────── */
    {
        /* `-f` arms alarm(5)+SIGALRM; with stdin held open and never fed the
         * decoder must give up by itself with a non-zero status. */
        int fds[2];
        pid_t pid;
        int status = 0;
        time_t t0, t1;

        if (pipe(fds) != 0) {
            ok(0, "pipe() for the flow-control probe");
        } else {
            pid = fork();
            if (pid == 0) {
                char *argv[] = { (char *)rtl_bin(), (char *)"-f",
                                 (char *)"-d", (char *)"3", NULL };
                dup2(fds[0], STDIN_FILENO);
                close(fds[0]);
                close(fds[1]);
                execvp(rtl_bin(), argv);
                _exit(127);
            }
            close(fds[0]);
            t0 = time(NULL);
            /* keep the write end open but silent -> decoder stalls */
            while (waitpid(pid, &status, 0) < 0 && errno == EINTR)
                ;
            t1 = time(NULL);
            close(fds[1]);
            ok(WIFEXITED(status) && WEXITSTATUS(status) != 0,
               "`-f` exits non-zero when stdin stalls (status %d)",
               WIFEXITED(status) ? WEXITSTATUS(status) : -1);
            /* The alarm itself is 5 s; the bound is deliberately loose because
             * a loaded CI worker can be slow to schedule the handler. What is
             * being proven is that the process gave up by itself instead of
             * blocking on read() forever — with the alarm compiled out (the
             * WINDOWS_BUILD path) it would never return. */
            ok(t1 - t0 <= 30, "`-f` gave up on its own, well before the harness "
               "would give up waiting (%lds elapsed, alarm is 5 s)", (long)(t1 - t0));
        }
    }

    {
        char *argv[] = { (char *)rtl_bin(), (char *)"-p", (char *)"X", NULL };
        pid_t pid = fork();
        int status = 0;
        if (pid == 0) {
            int null = open("/dev/null", O_RDONLY);
            if (null >= 0) {
                dup2(null, STDIN_FILENO);
                close(null);
            }
            execvp(rtl_bin(), argv);
            _exit(127);
        }
        while (waitpid(pid, &status, 0) < 0 && errno == EINTR)
            ;
        ok(WIFEXITED(status) && WEXITSTATUS(status) == 1,
           "getopt rejects an invalid `-p` mode with status 1 (got %d)",
           WIFEXITED(status) ? WEXITSTATUS(status) : -1);
    }

    {
        /* `-s` (S1 + T1/C1 simultaneously) on an empty capture: exits cleanly. */
        char *argv[] = { (char *)rtl_bin(), (char *)"-s", (char *)"-d",
                         (char *)"3", NULL };
        pid_t pid = fork();
        int status = 0, null;
        if (pid == 0) {
            null = open("/dev/null", O_RDONLY);
            if (null >= 0) {
                dup2(null, STDIN_FILENO);
                close(null);
            }
            execvp(rtl_bin(), argv);
            _exit(127);
        }
        while (waitpid(pid, &status, 0) < 0 && errno == EINTR)
            ;
        ok(WIFEXITED(status) && WEXITSTATUS(status) == 0,
           "`-s` combined S1+T1/C1 mode is accepted (status %d)",
           WIFEXITED(status) ? WEXITSTATUS(status) : -1);
    }

    printf("\n%d checks, %d failure(s)\n", checks, failures);
    return failures ? 1 : 0;
}
