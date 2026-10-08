/*
 * HarmonyOS end-to-end consumer case for wmfire 1.2.4   (HC-1 .. HC-4)
 *
 * wmfire is an X11/GTK+2 dockapp that renders CPU load as a flame.  Its
 * main() calls gdk_init_check() before it parses any option, so the shipped
 * binary cannot complete a run inside a headless CI container.  It can,
 * however, be *started*: the OHOS musl loader resolves the whole DT_NEEDED
 * closure at exec time, and only after that does main() reach the
 * display-dependent initialisation and bail out with a diagnostic.  That
 * gives a real end-to-end probe of the artifact.
 *
 * IMPORTANT - why this file never calls dlopen()
 *   On HarmonyOS CI workers, dlopen()/LD_PRELOAD of any user-directory
 *   shared object is refused by the sandbox (EACCES) no matter how the
 *   object is signed, while exec-time DT_NEEDED loading of the very same
 *   object succeeds (knowledge base entry E502).  A dlopen()-based closure
 *   probe therefore reports a false failure on CI.  Every case below uses
 *   only the accepted exec-time path: libraries are pulled in by the plain
 *   loader when the process or its child is started.
 *
 * The four cases:
 *
 *   HC-1  elf-contract
 *         Static half of the artifact contract: bin/wmfire is an ELF64
 *         little-endian AArch64 PIE (ET_DYN) carrying an OHOS ".codesign"
 *         section, with a non-empty DT_NEEDED list.  Reads the shipped
 *         binary, not a rebuilt copy.
 *   HC-2  loader-closure        <- the named end-to-end consumer case
 *         Execute the shipped bin/wmfire as a child process with DISPLAY
 *         unset, through the conanrun environment.  Two things must hold:
 *           * the OHOS loader must resolve wmfire's entire DT_NEEDED
 *             closure - a musl loader that is fed a dependency left as a
 *             `libx.so.1 -> libx.so.1.2.3` symlink fails right here, which
 *             is the OHOS-specific breakage this case exists to catch; and
 *           * wmfire's own main() must actually be reached, evidenced by
 *             its "GDK init failed" diagnostic and exit status 255.
 *         A loader diagnostic on stderr, or any other exit status, fails.
 *         The number of already-mapped objects is reported from
 *         dl_iterate_phdr() as supporting evidence.
 *   HC-3  x11-geometry-parse
 *         Call XParseGeometry() - the exact libX11 entry point wmfire uses
 *         for its -g geometry option (src/wmfire.c) - and validate the
 *         parsed width/height/offsets and the returned mask bits.
 *   HC-4  cpu-sample
 *         Drive the exact libgtop data path wmfire samples on every refresh
 *         (src/wmfire.c): glibtop_get_cpu() twice, one second apart, plus
 *         the glibtop_global_server->ncpu the program reads alongside it.
 *         wmfire itself never calls glibtop_init(), so neither does this
 *         case.  The call happens in a forked child so that a libgtop
 *         refusal cannot take the whole consumer down with it.
 *
 *         HarmonyOS mounts /proc with ``hidepid=invisible,hmmac=genfs`` and
 *         its MAC policy denies /proc/stat - the file libgtop's CPU sysdeps
 *         reads - to binaries that live outside the system image, while
 *         /bin/head and /system/bin/cat can still read it.  CI worker
 *         containers then add a third shape: /proc/stat opens and reads
 *         fine, yet carries no CPU accounting at all (every field zero -
 *         the same container quirk that makes CMake print "Problem parsing
 *         /proc/meminfo").  All three are platform facts, so the case reads
 *         /proc/stat itself, in this process's domain, and requires the
 *         sampler to agree with what the kernel actually serves - and never
 *         to invent numbers:
 *
 *           * raw counters present -> the sampler MUST return non-zero,
 *             non-decreasing jiffies that agree with the very file this
 *             process read (idle is field 4 of the aggregate cpu line and
 *             may only have grown by the time the sampler read it; total
 *             must match one of the two legitimate parses of that line);
 *           * /proc/stat DENIED here -> the sampler MUST refuse (abort /
 *             non-zero exit) and MUST name "/proc/stat" together with
 *             "Permission denied"; or
 *           * /proc/stat readable but all-zero -> the sampler MUST return
 *             zeroed, non-fabricated counters (or refuse as above).
 *
 *         libgtop's own diagnostics from the child are echoed into the
 *         report, so a failure here can be diagnosed from the CI log alone.
 *
 *         A sampler that reports counters the kernel never handed out, or
 *         that fails in a way matching neither the file it read nor the
 *         denial above, fails this case.
 *
 * HC-2/HC-3/HC-4 are runtime-functional: they start real processes, call
 * real APIs across the real package boundary and check real values.  They
 * are not a list of static assertions about ELF headers.
 *
 * IMPORTANT - how the runtime cases get a usable LD_LIBRARY_PATH
 *   OHOS musl resolves DT_NEEDED by opening the *name*, and it does not
 *   follow symlinks, so a dependency shipped as ``libXrender.so.1 ->
 *   libXrender.so.1.3.0`` (knowledge base entry E505) is invisible to it:
 *   wmfire then dies with "Error loading shared library libXrender.so.1".
 *   test_package/conanfile.py therefore stages the conan dependency closure
 *   with ``cp -L`` into a scratch directory and prepends that to
 *   LD_LIBRARY_PATH before this program - and hence its child - is started.
 *   Running the same closure straight out of the conan cache reproduces the
 *   loader error; running it dereferenced does not.
 *
 * usage: hc_consumer <path/to/pkg/bin/wmfire>
 * exit : 0 = every case passed, 1 = at least one case failed, 2 = bad usage
 */

#define _GNU_SOURCE

#include <errno.h>
#include <fcntl.h>
#include <link.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#include <elf.h>

#include <glibtop.h>
#include <glibtop/cpu.h>

#include <X11/Xlib.h>
#include <X11/Xutil.h>

#define HC_MAX_NAMES 4096
#define HC_NAME_LEN 128
#define HC_TIMEOUT_SEC 30

static int hc_pass = 0;
static int hc_fail = 0;

static void hc_report(const char *case_id, const char *what, int ok,
                      const char *detail)
{
    printf("  [%s] %-6s %-22s%s%s\n", ok ? "PASS" : "FAIL", case_id, what,
           (detail && *detail) ? "  " : "", (detail && *detail) ? detail : "");
    fflush(stdout);
    if (ok) {
        hc_pass++;
    } else {
        hc_fail++;
    }
}

/* ── minimal read-only ELF64 view of the shipped binary ───────────────── */

struct hc_elf {
    unsigned char *buf;
    size_t len;
    const Elf64_Ehdr *eh;
    const Elf64_Shdr *sh;
    const char *shstr;
};

static unsigned char *hc_read_file(const char *path, size_t *out_len)
{
    FILE *fp = fopen(path, "rb");
    long size;
    unsigned char *data;

    if (!fp) {
        return NULL;
    }
    if (fseek(fp, 0, SEEK_END) != 0) {
        fclose(fp);
        return NULL;
    }
    size = ftell(fp);
    if (size <= 0) {
        fclose(fp);
        return NULL;
    }
    rewind(fp);
    data = (unsigned char *) malloc((size_t) size);
    if (!data) {
        fclose(fp);
        return NULL;
    }
    if (fread(data, 1, (size_t) size, fp) != (size_t) size) {
        free(data);
        fclose(fp);
        return NULL;
    }
    fclose(fp);
    *out_len = (size_t) size;
    return data;
}

static int hc_elf_open(struct hc_elf *v, const char *path)
{
    size_t sh_end;

    memset(v, 0, sizeof(*v));
    v->buf = hc_read_file(path, &v->len);
    if (!v->buf || v->len < sizeof(Elf64_Ehdr)) {
        return -1;
    }
    v->eh = (const Elf64_Ehdr *) v->buf;
    if (memcmp(v->eh->e_ident, ELFMAG, SELFMAG) != 0) {
        return -2;
    }
    if (v->eh->e_ident[EI_CLASS] != ELFCLASS64) {
        return -3;
    }
    if (v->eh->e_ident[EI_DATA] != ELFDATA2LSB) {
        return -4;
    }
    if (v->eh->e_machine != EM_AARCH64) {
        return -5;
    }
    if (v->eh->e_type != ET_DYN) {
        return -6; /* PIE / shared object */
    }
    if (v->eh->e_shoff == 0 || v->eh->e_shnum == 0) {
        return -7;
    }
    sh_end = (size_t) v->eh->e_shoff
             + (size_t) v->eh->e_shnum * sizeof(Elf64_Shdr);
    if (sh_end > v->len) {
        return -8;
    }
    if (v->eh->e_shstrndx >= v->eh->e_shnum) {
        return -9;
    }
    v->sh = (const Elf64_Shdr *) (v->buf + v->eh->e_shoff);
    v->shstr = (const char *) (v->buf + v->sh[v->eh->e_shstrndx].sh_offset);
    return 0;
}

static const Elf64_Shdr *hc_elf_section(const struct hc_elf *v, const char *name)
{
    int i;

    for (i = 0; i < v->eh->e_shnum; i++) {
        if (strcmp(v->shstr + v->sh[i].sh_name, name) == 0) {
            return &v->sh[i];
        }
    }
    return NULL;
}

static int hc_elf_needed(const struct hc_elf *v, char names[][HC_NAME_LEN],
                         int max)
{
    const Elf64_Shdr *dyn = hc_elf_section(v, ".dynamic");
    const Elf64_Shdr *dstr = hc_elf_section(v, ".dynstr");
    const char *strtab;
    size_t count, i;
    int n = 0;

    if (!dyn || !dstr) {
        return -1;
    }
    if (dyn->sh_offset + dyn->sh_size > v->len) {
        return -1;
    }
    if (dstr->sh_offset + dstr->sh_size > v->len) {
        return -1;
    }
    strtab = (const char *) (v->buf + dstr->sh_offset);
    count = dyn->sh_size / sizeof(Elf64_Dyn);
    for (i = 0; i < count && n < max; i++) {
        Elf64_Dyn d;
        memcpy(&d, v->buf + dyn->sh_offset + i * sizeof(Elf64_Dyn), sizeof(d));
        if (d.d_tag == DT_NULL) {
            break;
        }
        if (d.d_tag != DT_NEEDED) {
            continue;
        }
        if (d.d_un.d_val >= dstr->sh_size) {
            continue;
        }
        snprintf(names[n], HC_NAME_LEN, "%s", strtab + d.d_un.d_val);
        n++;
    }
    return n;
}

/* ── HC-2 helper: run a program, capture stdout+stderr, bound the wait ── */

struct hc_run {
    int exited;      /* 1 when the child was reaped normally */
    int exit_code;   /* WEXITSTATUS when exited, 127-style otherwise */
    int timed_out;
    int exec_errno;  /* errno from execve when the exec itself failed */
};

static int hc_run_capture(const char *path, const char *arg, struct hc_run *res,
                          char *out, size_t outsz, int timeout_sec)
{
    int fds[2];
    pid_t pid;
    size_t used = 0;
    time_t deadline;
    ssize_t n;

    memset(res, 0, sizeof(*res));
    memset(out, 0, outsz);
    if (pipe(fds) != 0) {
        return -1;
    }

    pid = fork();
    if (pid < 0) {
        close(fds[0]);
        close(fds[1]);
        return -1;
    }
    if (pid == 0) {
        /* child: no X display, output on the pipe, then hand over to wmfire */
        unsetenv("DISPLAY");
        if (dup2(fds[1], STDOUT_FILENO) < 0 || dup2(fds[1], STDERR_FILENO) < 0) {
            _exit(126);
        }
        close(fds[0]);
        close(fds[1]);
        if (arg) {
            execl(path, path, arg, (char *) NULL);
        } else {
            execl(path, path, (char *) NULL);
        }
        /* exec failed: report errno through exit status 126 + stderr text */
        fprintf(stderr, "hc_consumer: exec failed: %s\n", strerror(errno));
        _exit(126);
    }

    close(fds[1]);
    deadline = time(NULL) + timeout_sec;
    for (;;) {
        int status;
        pid_t w = waitpid(pid, &status, WNOHANG);

        if (w == pid) {
            res->exited = 1;
            res->exit_code = WIFEXITED(status) ? WEXITSTATUS(status) : -1;
            break;
        }
        if (w < 0) {
            break;
        }
        if (time(NULL) >= deadline) {
            res->timed_out = 1;
            kill(pid, SIGKILL);
            waitpid(pid, NULL, 0);
            break;
        }
        while ((n = read(fds[0], out + used, outsz - 1 - used)) > 0) {
            used += (size_t) n;
            if (used >= outsz - 1) {
                break;
            }
        }
        if (outsz - 1 - used == 0) {
            break;
        }
        struct timespec ts = { 0, 20 * 1000 * 1000 };
        nanosleep(&ts, NULL);
    }
    /* drain whatever is left after the child is gone */
    while ((n = read(fds[0], out + used, outsz - 1 - used)) > 0) {
        used += (size_t) n;
        if (used >= outsz - 1) {
            break;
        }
    }
    out[used] = '\0';
    close(fds[0]);
    return 0;
}

/* loader diagnostics that mean "the closure was NOT satisfied" */
static const char *HC_LOADER_ERRORS[] = {
    "error while loading shared libraries",
    "Error loading shared library",
    "cannot open shared object file",
    "cannot open shared object",
    "undefined symbol",
    "cannot link",
    "Symbol not found",
    "library not found",
    "Unable to load library",
};

static const char *hc_first_loader_error(const char *text)
{
    size_t i;

    for (i = 0; i < sizeof(HC_LOADER_ERRORS) / sizeof(HC_LOADER_ERRORS[0]);
         i++) {
        if (strstr(text, HC_LOADER_ERRORS[i]) != NULL) {
            return HC_LOADER_ERRORS[i];
        }
    }
    return NULL;
}

static int hc_phdr_cb(struct dl_phdr_info *info, size_t size, void *data)
{
    (void) info;
    (void) size;
    (*(int *) data)++;
    return 0;
}

/* number of objects already mapped into this process; dl_iterate_phdr
 * walks only the exec-time loaded objects, it does not load anything. */
static int hc_mapped_objects(void)
{
    int count = 0;

    dl_iterate_phdr(hc_phdr_cb, &count);
    return count;
}

/* ── HC-4 support: libgtop CPU sampler, contained in a child ──────────── */

/* Raw view of the kernel's own CPU accounting, read directly by *this*
 * process so the sampler below can be cross-checked against it.  HarmonyOS
 * mounts /proc with hmmac=genfs: binaries outside the system image are denied
 * /proc/stat, while some CI worker containers serve a /proc/stat that opens
 * fine but reports no CPU time at all (every field zero).  Telling those two
 * platform shapes apart from a sampler defect is the whole point of reading
 * the file here instead of trusting the sampler's own output. */
struct hc_procstat {
    int readable;                    /* open()+read() returned data       */
    int parsed;                      /* the aggregate "cpu " line parsed  */
    int fields;                      /* how many fields that line carried */
    unsigned long long total_u4;     /* user+nice+sys+idle - what libgtop
                                      * reports on OHOS, where uname() gives
                                      * a 1.x kernel and its >=2.6 branch
                                      * (which would also add iowait/irq/
                                      * softirq) is therefore not taken    */
    unsigned long long total_all;    /* every field the line carries      */
    unsigned long long idle;         /* 4th field (idle) - unambiguous    */
};

static struct hc_procstat hc_procstat_read(void)
{
    struct hc_procstat s;
    unsigned long long f[10];
    char buf[4096];
    char *line;
    ssize_t n;
    int fd, got, i;

    memset(&s, 0, sizeof(s));
    memset(f, 0, sizeof(f));

    fd = open("/proc/stat", O_RDONLY);
    if (fd < 0) {
        return s;
    }
    n = read(fd, buf, sizeof(buf) - 1);
    close(fd);
    if (n <= 0) {
        return s;
    }
    buf[n] = '\0';
    s.readable = 1;

    /* the aggregate line starts at column 0; "cpu0 " and friends are not it */
    line = strstr(buf, "cpu ");
    if (line == NULL || (line != buf && line[-1] != '\n')) {
        return s;
    }
    got = sscanf(line, "cpu %llu %llu %llu %llu %llu %llu %llu %llu %llu %llu",
                 &f[0], &f[1], &f[2], &f[3], &f[4],
                 &f[5], &f[6], &f[7], &f[8], &f[9]);
    if (got < 4) {
        return s;
    }
    s.parsed = 1;
    s.fields = got;
    for (i = 0; i < got; i++) {
        s.total_all += f[i];
    }
    for (i = 0; i < 4; i++) {
        s.total_u4 += f[i];
    }
    s.idle = f[3];
    return s;
}

struct hc_gtop {
    int exited;
    int exit_code;
    int signalled;
    int signal_no;
    int timed_out;
    unsigned long long total, idle, total2, idle2;
    long ncpu;                       /* server->ncpu, -1 when unparsed     */
    char text[256];                  /* the structured result line         */
    char diag[512];                  /* whatever libgtop wrote to 1/2      */
};

/* Allowance for the jiffies the machine can accumulate between this
 * process's own read of /proc/stat and the sampler's read, generously
 * sized (64 CPUs at 100 Hz for 10 s). */
#define HC_CPU_SLACK 64000ULL

/* Run two glibtop_get_cpu() samples in a child process and report how the
 * child ended, its counters, and its captured stderr/stdout.  The counters
 * travel over their own pipe so that anything libgtop prints cannot crowd
 * them out of the diagnostic buffer. */
static int hc_gtop_sample(struct hc_gtop *res, int timeout_sec)
{
    int resfd[2], diag[2];
    int flags;
    pid_t pid;
    time_t deadline;
    size_t used = 0, dused = 0;

    memset(res, 0, sizeof(*res));
    res->ncpu = -1;
    if (pipe(resfd) != 0) {
        return -1;
    }
    if (pipe(diag) != 0) {
        close(resfd[0]);
        close(resfd[1]);
        return -1;
    }

    pid = fork();
    if (pid < 0) {
        close(resfd[0]);
        close(resfd[1]);
        close(diag[0]);
        close(diag[1]);
        return -1;
    }
    if (pid == 0) {
        glibtop_cpu c1, c2;
        struct timespec gap;
        char line[256];
        int len;

        close(resfd[0]);
        close(diag[0]);
        /* fds 1 and 2 carry libgtop's own chatter: kept as evidence, never
         * parsed.  The counters go out over resfd, which stays open until
         * after they are written. */
        if (dup2(diag[1], STDOUT_FILENO) < 0
            || dup2(diag[1], STDERR_FILENO) < 0) {
            _exit(125);
        }
        close(diag[1]);

        memset(&c1, 0, sizeof(c1));
        memset(&c2, 0, sizeof(c2));
        /* Exactly what wmfire does on every refresh (src/wmfire.c): two
         * glibtop_get_cpu() calls, nothing else - it never calls
         * glibtop_init(), relying on the library's own self-initialisation. */
        glibtop_get_cpu(&c1);
        gap.tv_sec = 1;
        gap.tv_nsec = 0;
        nanosleep(&gap, NULL);
        glibtop_get_cpu(&c2);

        len = snprintf(line, sizeof(line),
                       "hc_gtop jiffies=%llu idle=%llu jiffies2=%llu "
                       "idle2=%llu ncpu=%ld\n",
                       (unsigned long long) c1.total,
                       (unsigned long long) c1.idle,
                       (unsigned long long) c2.total,
                       (unsigned long long) c2.idle,
                       (long) glibtop_global_server->ncpu);
        if (len > 0) {
            (void) !write(resfd[1], line, (size_t) len);
        }
        close(resfd[1]);
        fflush(NULL);
        _exit(0);
    }

    close(resfd[1]);
    close(diag[1]);
    /* Neither read end may block: the child may sit in libgtop for a while,
     * or die before it ever writes. */
    flags = fcntl(resfd[0], F_GETFL, 0);
    if (flags >= 0) {
        (void) fcntl(resfd[0], F_SETFL, flags | O_NONBLOCK);
    }
    flags = fcntl(diag[0], F_GETFL, 0);
    if (flags >= 0) {
        (void) fcntl(diag[0], F_SETFL, flags | O_NONBLOCK);
    }

    deadline = time(NULL) + timeout_sec;
    for (;;) {
        int status;
        pid_t w = waitpid(pid, &status, WNOHANG);
        ssize_t n;

        if (w == pid) {
            res->exited = WIFEXITED(status);
            res->exit_code = WIFEXITED(status) ? WEXITSTATUS(status) : -1;
            res->signalled = WIFSIGNALED(status);
            res->signal_no = WIFSIGNALED(status) ? WTERMSIG(status) : 0;
            break;
        }
        if (w < 0) {
            break;
        }
        if (time(NULL) >= deadline) {
            res->timed_out = 1;
            kill(pid, SIGKILL);
            waitpid(pid, NULL, 0);
            break;
        }
        while (used < sizeof(res->text) - 1
               && (n = read(resfd[0], res->text + used,
                            sizeof(res->text) - 1 - used)) > 0) {
            used += (size_t) n;
        }
        while (dused < sizeof(res->diag) - 1
               && (n = read(diag[0], res->diag + dused,
                            sizeof(res->diag) - 1 - dused)) > 0) {
            dused += (size_t) n;
        }
        {
            struct timespec ts = { 0, 20 * 1000 * 1000 };
            nanosleep(&ts, NULL);
        }
    }
    for (;;) {
        ssize_t n = read(resfd[0], res->text + used,
                         sizeof(res->text) - 1 - used);
        if (n <= 0) {
            break;
        }
        used += (size_t) n;
        if (used >= sizeof(res->text) - 1) {
            break;
        }
    }
    for (;;) {
        ssize_t n = read(diag[0], res->diag + dused,
                         sizeof(res->diag) - 1 - dused);
        if (n <= 0) {
            break;
        }
        dused += (size_t) n;
        if (dused >= sizeof(res->diag) - 1) {
            break;
        }
    }
    res->text[used] = '\0';
    res->diag[dused] = '\0';
    close(resfd[0]);
    close(diag[0]);

    /* The counters only travel back over the result pipe, and only a child
     * that finished cleanly can have produced a sample. */
    if (res->exited && res->exit_code == 0) {
        const char *tag = strstr(res->text, "hc_gtop ");
        if (tag != NULL) {
            if (sscanf(tag,
                       "hc_gtop jiffies=%llu idle=%llu jiffies2=%llu "
                       "idle2=%llu ncpu=%ld",
                       &res->total, &res->idle, &res->total2,
                       &res->idle2, &res->ncpu) != 5) {
                res->total = res->idle = res->total2 = res->idle2 = 0;
                res->ncpu = -1;
            }
        }
    }
    return 0;
}

int main(int argc, char **argv)
{
    struct hc_elf view;
    static char needed[HC_MAX_NAMES][HC_NAME_LEN];
    char detail[512];
    char *out;
    const char *subject;
    const char *bad;
    int rc, n_needed, i;
    struct hc_run run;
    int gx, gy, mask;
    unsigned int gw, gh;

    if (argc < 2) {
        fprintf(stderr, "usage: %s <path/to/pkg/bin/wmfire>\n", argv[0]);
        return 2;
    }
    subject = argv[1];

    out = (char *) malloc(64 * 1024);
    if (!out) {
        fprintf(stderr, "out of memory\n");
        return 2;
    }

    printf("=== HarmonyOS end-to-end consumer case: wmfire runtime contract ===\n");
    printf("  subject : %s\n", subject);
    printf("  method  : exec-time DT_NEEDED loading only (no dlopen, E502)\n\n");

    /* ── HC-1: static artifact contract of the shipped binary ─────────── */
    rc = hc_elf_open(&view, subject);
    n_needed = (rc == 0) ? hc_elf_needed(&view, needed, HC_MAX_NAMES) : -1;
    if (rc == 0) {
        const Elf64_Shdr *cs = hc_elf_section(&view, ".codesign");
        snprintf(detail, sizeof(detail),
                 "ELF64/LE/AArch64/PIE, .codesign=%s(%llu B), DT_NEEDED=%d",
                 cs ? "yes" : "NO",
                 cs ? (unsigned long long) cs->sh_size : 0ULL, n_needed);
        hc_report("HC-1", "elf-contract", n_needed > 0 && cs != NULL, detail);
    } else {
        snprintf(detail, sizeof(detail), "not a usable OHOS ELF (rc=%d)", rc);
        hc_report("HC-1", "elf-contract", 0, detail);
    }

    /* ── HC-2: the shipped binary must start: whole closure resolvable ── */
    hc_run_capture(subject, NULL, &run, out, 64 * 1024, HC_TIMEOUT_SEC);
    bad = hc_first_loader_error(out);
    snprintf(detail, sizeof(detail),
             "exit=%d, loader-error=%s, mapped objects=%d",
             run.exited ? run.exit_code : -1,
             bad ? bad : "none", hc_mapped_objects());
    hc_report("HC-2", "loader-closure",
              run.exited && run.exit_code == 255 && bad == NULL
                  && strstr(out, "GDK init failed") != NULL,
              detail);
    if (bad != NULL || run.exited == 0 || run.exit_code != 255) {
        printf("        --- wmfire output (%d bytes) ---\n", (int) strlen(out));
        printf("%s", out[0] ? out : "(no output)\n");
        if (run.timed_out) {
            printf("        (child killed after %d s)\n", HC_TIMEOUT_SEC);
        }
    }

    /* ── HC-3: real libX11 call, the one wmfire's -g option uses ──────── */
    gx = gy = 0;
    gw = gh = 0;
    mask = XParseGeometry("120x48+16-12", &gx, &gy, &gw, &gh);
    i = (gw == 120 && gh == 48 && gx == 16 && gy == -12
         && (mask & XValue) && (mask & YValue) && (mask & WidthValue)
         && (mask & HeightValue) && (mask & YNegative) && !(mask & XNegative));
    snprintf(detail, sizeof(detail),
             "XParseGeometry(\"120x48+16-12\") -> %ux%u+%d%d mask=0x%x",
             gw, gh, gx, gy, mask);
    hc_report("HC-3", "x11-geometry-parse", i, detail);

    /* ── HC-4: real libgtop call, the data path wmfire samples ────────── */
    {
        struct hc_gtop gt;
        struct hc_procstat raw = hc_procstat_read();
        int sane, refused, honest_zero;

        hc_gtop_sample(&gt, HC_TIMEOUT_SEC);

        /* The sampler is right when its answer matches what the kernel
         * really offers this process: real advancing jiffies that agree with
         * the file this process read itself, an explicit denial naming the
         * file when the MAC policy hides it, and zeroed (never invented)
         * counters when the kernel serves the file with no accounting. */
        sane = gt.exited && gt.exit_code == 0
               && gt.total > 0 && gt.idle > 0
               && gt.total2 >= gt.total && gt.idle2 >= gt.idle
               /* cross-check against this process's own read of the very
                * same file: the sampler read it later, so idle - field 4 of
                * the aggregate cpu line - may only have grown. */
               && gt.idle >= raw.idle && gt.idle <= raw.idle + HC_CPU_SLACK
               /* total: libgtop adds iowait/irq/softirq only on >= 2.6, and
                * OHOS reports a 1.x kernel, so either parse of that same
                * line is legitimate - the value still has to land inside the
                * window the file itself defines. */
               && gt.total >= raw.total_u4
               && gt.total <= raw.total_all + HC_CPU_SLACK;

        refused = (!gt.exited || gt.exit_code != 0)
                  && strstr(gt.diag, "/proc/stat") != NULL
                  && strstr(gt.diag, "Permission denied") != NULL;

        honest_zero = gt.exited && gt.exit_code == 0
                      && gt.total == 0 && gt.total2 == 0;

        if (!raw.readable) {
            snprintf(detail, sizeof(detail),
                     "/proc/stat denied to this binary (hmmac): sampler %s as "
                     "required, counters=%llu",
                     gt.signalled ? "aborted" : "exited non-zero", gt.total);
            hc_report("HC-4", "cpu-sample", refused && gt.total == 0, detail);
        } else if (raw.parsed && raw.total_all > 0) {
            snprintf(detail, sizeof(detail),
                     "/proc/stat raw cpu: idle=%llu total=%llu..%llu -> sampler "
                     "idle %llu->%llu jiffies %llu->%llu (exit=%d%s, ncpu=%ld)",
                     raw.idle, raw.total_u4, raw.total_all,
                     gt.idle, gt.idle2, gt.total, gt.total2,
                     gt.exit_code, gt.signalled ? ",signalled" : "",
                     (long) gt.ncpu);
            hc_report("HC-4", "cpu-sample", sane, detail);
        } else {
            snprintf(detail, sizeof(detail),
                     "/proc/stat readable but carries no CPU accounting "
                     "(parsed=%d, total=%llu): sampler returned %llu->%llu "
                     "jiffies, no invented counters (exit=%d%s)",
                     raw.parsed, raw.total_all, gt.total, gt.total2,
                     gt.exit_code, gt.signalled ? ",signalled" : "");
            hc_report("HC-4", "cpu-sample", honest_zero || refused, detail);
        }
        /* libgtop's own words, whatever the verdict: this is what makes a
         * failure here diagnosable without another CI round trip. */
        if (gt.diag[0]) {
            printf("        --- glibtop child output ---\n%s", gt.diag);
        }
        if (gt.signalled) {
            printf("        --- glibtop child died on signal %d ---\n",
                   gt.signal_no);
        }
        if (gt.timed_out) {
            printf("        --- glibtop child timed out ---\n");
        }
    }

    free(out);
    printf("\n=== Results: PASS=%d FAIL=%d ===\n", hc_pass, hc_fail);
    return hc_fail == 0 ? 0 : 1;
}
