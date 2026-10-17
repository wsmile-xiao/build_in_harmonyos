/* test_matroxset.c — consumer-side test for the packaged matroxset 0.4 binary.
 *
 * R34: this test genuinely depends on the package under test. Every CLI check
 * really executes the packaged `matroxset` executable (located through
 * $MATROXSET_BIN, or via PATH when the test runs under `env="conanrun"`) and
 * asserts on its real stdout/stderr text **and** its real exit status. If the
 * package's bin/ is removed the binary cannot be executed and every check
 * fails (this is what CI's L1e destructive reverse test verifies).
 *
 * matroxset normally drives Matrox fbdev ioctls, so no Matrox hardware is
 * needed: the paths exercised below are all decided *before* any ioctl, plus
 * three that reach the ioctl stage on /dev/null and must report the failure.
 *
 * HarmonyOS-specific checks (the ELF/loader block at the end) are real
 * platform assertions, not decoration:
 *   - the packaged tool must be an AArch64 ELF (EM_AARCH64 = 183);
 *   - it must be a PIE (ET_DYN), the OHOS hardening baseline;
 *   - it must carry **no DT_NEEDED on a ncurses shared object**. The OHOS
 *     ncurses package ships static archives only and the OHOS loader ignores
 *     LD_LIBRARY_PATH, so a dynamically linked matroxset would fail to start
 *     on a clean device. Parsing .dynamic proves the static link really holds.
 */
#include <elf.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>

#ifndef EM_AARCH64
#define EM_AARCH64 183
#endif

#define MAT_MAX_NEEDED 256

static int g_pass;
static int g_fail;

static const char *mat_bin(void)
{
    const char *p = getenv("MATROXSET_BIN");
    return (p && *p) ? p : "matroxset";
}

static void check(int cond, const char *fmt, ...)
{
    va_list ap;
    va_start(ap, fmt);
    if (cond) {
        g_pass++;
        printf("PASS: ");
    } else {
        g_fail++;
        printf("FAIL: ");
    }
    vprintf(fmt, ap);
    printf("\n");
    fflush(stdout);
    va_end(ap);
}

/* Append s to dst as a single-quoted shell word. Returns -1 if it would not
 * fit, so a long path can never silently truncate the command. */
static int append_quoted(char *dst, size_t cap, const char *s)
{
    size_t n = strlen(dst);

    if (n + 4 >= cap)
        return -1;
    dst[n++] = '\'';
    for (; *s; s++) {
        if (*s == '\'') {
            if (n + 5 >= cap)
                return -1;
            dst[n++] = '\'';
            dst[n++] = '\\';
            dst[n++] = '\'';
            dst[n++] = '\'';
        } else {
            if (n + 2 >= cap)
                return -1;
            dst[n++] = *s;
        }
    }
    dst[n++] = '\'';
    dst[n] = '\0';
    return 0;
}

/* Run matroxset with the given args, capture merged stdout+stderr.
 * Returns the exit status; *out receives a malloc'd NUL-terminated buffer. */
static int run_matroxset(char *const argv[], char **out)
{
    size_t cap = 8192;
    size_t len = 0;
    char *buf = malloc(cap);
    char cmd[4096];
    size_t l;
    int i;
    int rc;

    if (!buf) {
        fprintf(stderr, "OOM\n");
        exit(2);
    }
    buf[0] = '\0';
    *out = buf;

    /* Build the command out of single-quoted shell words only. */
    cmd[0] = '\0';
    if (append_quoted(cmd, sizeof(cmd), mat_bin()) != 0)
        return -1;
    for (i = 0; argv[i]; i++) {
        l = strlen(cmd);
        if (l + 2 >= sizeof(cmd))
            return -1;
        cmd[l] = ' ';
        cmd[l + 1] = '\0';
        if (append_quoted(cmd, sizeof(cmd), argv[i]) != 0)
            return -1;
    }
    l = strlen(cmd);
    if (l + 8 >= sizeof(cmd))
        return -1;
    strcpy(cmd + l, " 2>&1");

    FILE *fp = popen(cmd, "r");
    if (!fp) {
        free(buf);
        *out = NULL;
        return -1;
    }
    for (;;) {
        size_t got = fread(buf + len, 1, cap - len - 1, fp);
        if (got == 0)
            break;
        len += got;
        buf[len] = '\0';
    }
    rc = pclose(fp);
    /* pclose() returns a wait(2) status, not the bare exit code, so the
     * child's exit status has to be extracted with the WEXITSTATUS shift. */
    if (rc == -1 || !WIFEXITED(rc))
        return -1;
    return WEXITSTATUS(rc);
}

static int run_and_report(char *const argv[], const char *expect_sub,
                          int expect_rc, const char *label)
{
    char *out = NULL;
    int rc = run_matroxset(argv, &out);
    int has_text = (expect_sub == NULL) ||
                   (out && strstr(out, expect_sub) != NULL);

    check(rc == expect_rc && has_text,
          "%s: rc=%d (want %d), output %s\"%.180s\"",
          label, rc, expect_rc, has_text ? "contains " : "MISSING ",
          out ? out : "");
    free(out);
    return rc;
}

/* ── HarmonyOS ELF/loader assertions ──────────────────────────────────── */

/* 0 = ELF64 AArch64, 1 = wrong machine, -1 = not an ELF64 file / unreadable */
static int elf_is_aarch64(const char *path)
{
    unsigned char hdr[64];
    Elf64_Ehdr eh;
    FILE *fp = fopen(path, "rb");

    if (!fp)
        return -1;
    if (fread(hdr, 1, sizeof(hdr), fp) != sizeof(hdr)) {
        fclose(fp);
        return -1;
    }
    fclose(fp);
    if (memcmp(hdr, ELFMAG, SELFMAG) != 0)
        return -1;
    memcpy(&eh, hdr, sizeof(eh));
    if (eh.e_ident[EI_CLASS] != ELFCLASS64)
        return -1;
    return (eh.e_machine == EM_AARCH64) ? 0 : 1;
}

static int elf_is_pie(const char *path)
{
    unsigned char hdr[64];
    Elf64_Ehdr eh;
    FILE *fp = fopen(path, "rb");

    if (!fp)
        return -1;
    if (fread(hdr, 1, sizeof(hdr), fp) != sizeof(hdr)) {
        fclose(fp);
        return -1;
    }
    fclose(fp);
    if (memcmp(hdr, ELFMAG, SELFMAG) != 0)
        return -1;
    memcpy(&eh, hdr, sizeof(eh));
    return (eh.e_type == ET_DYN) ? 0 : 1;
}

/* 1 = some DT_NEEDED mentions ncurses, 0 = none, -1 = unreadable/inconclusive.
 * -1 is deliberately distinguishable from 0: an unparsable ELF must FAIL the
 * check rather than be silently reported as "no dynamic ncurses". */
static int elf_dynamic_needs_ncurses(const char *path)
{
    unsigned char *img = NULL;
    long size;
    Elf64_Ehdr *eh;
    Elf64_Phdr *ph;
    Elf64_Dyn *dyn;
    Elf64_Word need_off[MAT_MAX_NEEDED];
    Elf64_Xword strtab_va = 0, strtab_sz = 0;
    Elf64_Xword n_dyn = 0;
    int i, k, n_need = 0, found = -1;
    FILE *fp;

    fp = fopen(path, "rb");
    if (!fp)
        return -1;
    if (fseek(fp, 0, SEEK_END) != 0) {
        fclose(fp);
        return -1;
    }
    size = ftell(fp);
    rewind(fp);
    if (size <= 0 || (unsigned long)size < sizeof(Elf64_Ehdr)) {
        fclose(fp);
        return -1;
    }
    img = malloc((size_t)size);
    if (!img || fread(img, 1, (size_t)size, fp) != (size_t)size) {
        free(img);
        fclose(fp);
        return -1;
    }
    fclose(fp);

    eh = (Elf64_Ehdr *)img;
    if (memcmp(eh->e_ident, ELFMAG, SELFMAG) != 0 ||
        eh->e_ident[EI_CLASS] != ELFCLASS64 ||
        eh->e_phoff + (size_t)eh->e_phnum * sizeof(Elf64_Phdr) > (size_t)size) {
        free(img);
        return -1;
    }
    ph = (Elf64_Phdr *)(img + eh->e_phoff);
    for (i = 0; i < eh->e_phnum; i++) {
        if (ph[i].p_type == PT_DYNAMIC &&
            ph[i].p_offset + ph[i].p_filesz <= (Elf64_Xword)size) {
            dyn = (Elf64_Dyn *)(img + ph[i].p_offset);
            n_dyn = ph[i].p_filesz / sizeof(Elf64_Dyn);
            /* Bounded walk: never read past PT_DYNAMIC's own file size. */
            for (k = 0; k < (int)n_dyn && dyn[k].d_tag != DT_NULL; k++) {
                if (dyn[k].d_tag == DT_NEEDED && n_need < MAT_MAX_NEEDED)
                    need_off[n_need++] = (Elf64_Word)dyn[k].d_un.d_val;
                else if (dyn[k].d_tag == DT_STRTAB)
                    strtab_va = dyn[k].d_un.d_val;
                else if (dyn[k].d_tag == DT_STRSZ)
                    strtab_sz = dyn[k].d_un.d_val;
            }
            break;
        }
    }
    if (n_dyn == 0) {
        free(img);
        return 0; /* no PT_DYNAMIC at all: nothing is loaded dynamically */
    }
    if (n_need == 0) {
        free(img);
        return 0;
    }
    if (strtab_va == 0 || strtab_sz == 0) {
        free(img);
        return -1; /* DT_NEEDED present but no string table: inconclusive */
    }
    /* Translate the DT_STRTAB virtual address into a file offset. */
    for (i = 0; i < eh->e_phnum; i++) {
        Elf64_Xword lo, hi, off;
        const char *strtab;
        if (ph[i].p_type != PT_LOAD)
            continue;
        lo = ph[i].p_vaddr;
        hi = lo + ph[i].p_filesz;
        if (strtab_va < lo || strtab_va >= hi)
            continue;
        off = ph[i].p_offset + (strtab_va - lo);
        if (off >= (Elf64_Xword)size) {
            free(img);
            return -1;
        }
        strtab = (const char *)(img + off);
        found = 0;
        for (k = 0; k < n_need; k++) {
            const char *name;
            /* Every DT_NEEDED offset must lie inside DT_STRSZ. */
            if ((Elf64_Xword)need_off[k] >= strtab_sz) {
                free(img);
                return -1;
            }
            name = strtab + need_off[k];
            if (name[0] && strstr(name, "ncurses")) {
                found = 1;
                break;
            }
        }
        break;
    }
    free(img);
    return found < 0 ? -1 : found;
}

/* Publish the real assertion counts so test_package/conanfile.py never has to
 * hardcode them (a hardcoded count silently becomes a false claim as soon as an
 * assertion is added or removed). */
static void write_counts(void)
{
    const char *path = getenv("MATROXSET_TEST_COUNTS");
    FILE *fp;

    if (!path || !*path)
        return;
    fp = fopen(path, "w");
    if (!fp)
        return;
    fprintf(fp, "passed=%d\nfailed=%d\ntotal=%d\n",
            g_pass, g_fail, g_pass + g_fail);
    fclose(fp);
}

int main(void)
{
    char *a_h[] = {(char *)"-h", NULL};
    char *a_bad[] = {(char *)"-Z", NULL};
    char *a_pm[] = {(char *)"-p", (char *)"-m", NULL};
    char *a_mo[] = {(char *)"-m", (char *)"-o", (char *)"1", NULL};
    char *a_noent[] = {(char *)"-f", (char *)"/nonexistent/fb0", NULL};
    char *a_devnull[] = {(char *)"-f", (char *)"/dev/null", NULL};
    char *a_list[] = {(char *)"-l", (char *)"-f", (char *)"/dev/null", NULL};
    char *a_ctrl[] = {(char *)"-c", (char *)"1", (char *)"-f", (char *)"/dev/null", NULL};
    const char *bin = mat_bin();

    printf("matroxset test binary under test: %s\n", bin);

    /* 1-3. usage text (upstream prints it to stderr and exits 98) */
    run_and_report(a_h, "usage: matroxset [-f fbdev] [-o output] [-m] [value]",
                   98, "usage banner");
    run_and_report(a_h, "(default /dev/fb1)", 98, "usage documents default fbdev");
    run_and_report(a_h, "print information about blanking", 98,
                   "usage documents -p");
    run_and_report(a_h, "For output mode, 128 means monitor, 1 = PAL TV, 2 = NTSC TV",
                   98, "usage documents output modes");
    /* 5. unknown option -> "Bad commandline", exit 99 */
    run_and_report(a_bad, "Bad commandline", 99, "unknown option rejected");
    /* 6. -p together with -m/-o is refused, exit 95 */
    run_and_report(a_pm, "You cannot use -p together with -m or -o", 95,
                   "-p + -m refused");
    /* 7. -m together with -o is refused, exit 96 */
    run_and_report(a_mo, "You cannot use -m and -o together", 96,
                   "-m + -o refused");
    /* 8. unopenable framebuffer -> strerror(errno), exit 122 */
    run_and_report(a_noent, "Cannot open /nonexistent/fb0: No such file or directory",
                   122, "unopenable fbdev reported");

    /* 9. reaches the ioctl stage: /dev/null opens fine, MATROXFB_GET_OUTPUT_MODE
     *    fails, so the tool must report the ioctl error and still exit 0. */
    run_and_report(a_devnull, "ioctl failed:", 0, "ioctl stage reached");
    /* 10. -l (list controls) prints the control table header/footer */
    run_and_report(a_list, "|Id      |Curr |Def. |Min  |Max  |Name", 0,
                   "-l prints control table");
    /* 11. -c <id> (get control) also reaches the ioctl stage */
    run_and_report(a_ctrl, "ioctl failed:", 0, "-c reaches ioctl stage");

    /* ── HarmonyOS-specific ─────────────────────────────────────────── */
    check(elf_is_aarch64(bin) == 0,
          "OHOS: packaged binary is an ELF64 AArch64 object (EM_AARCH64=%d)",
          EM_AARCH64);
    check(elf_is_pie(bin) == 0,
          "OHOS: packaged binary is position independent (ET_DYN)");
    check(elf_dynamic_needs_ncurses(bin) == 0,
          "OHOS: binary needs no ncurses shared object at run time "
          "(static link; the OHOS loader ignores LD_LIBRARY_PATH)");

    printf("\nRESULT: %d passed, %d failed, %d total\n",
           g_pass, g_fail, g_pass + g_fail);
    printf("HMBS_ASSERTIONS: passed=%d failed=%d total=%d\n",
           g_pass, g_fail, g_pass + g_fail);
    write_counts();
    return g_fail == 0 ? 0 : 1;
}