/*
 * test_shush.c - HarmonyOS PC consumer test for the packaged shush binary.
 *
 * One executable, three roles:
 *
 *   test_shush run <shush> <helper> <workdir>
 *       Driver.  Writes shush configurations under <workdir>, runs the
 *       packaged shush and checks what it did (exit status, reports,
 *       kept logs, diagnostics).
 *   test_shush -t -i
 *       sendmail(1) stand-in: shush pipes every report to
 *       "<sendmail> -t -i".  HarmonyOS PC ships no MTA, so the message is
 *       stored in $SHUSH_TEST_SPOOL for the driver to inspect.
 *   test_shush job <mode>
 *       The command supervised by shush (run through its shell).
 *
 * <helper> is the path shush uses for the two latter roles, normally this
 * very executable.  Exit status 0 only if every executed check passed.
 */
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <time.h>
#include <unistd.h>

#define MAX_MAILS 8

static const char *shush, *helper;
static char cfgdir[PATH_MAX], crondir[PATH_MAX], spooldir[PATH_MAX];
static char tmpdir[PATH_MAX], logdir[PATH_MAX];
static int passed, failed, notrun;

struct buf {
    char *data;
    size_t len;
};

struct result {
    int rc;             /* exit code, or 128 + signal */
    double secs;
    struct buf out, err;
};

static void check(const char *id, int ok, const char *fmt, ...)
{
    va_list ap;

    printf("%s [%s] ", ok ? "PASS" : "FAIL", id);
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
    printf("\n");
    if (ok)
        passed++;
    else
        failed++;
}

/* Byte search: fatal() in shush writes a NUL into stderr. */
static int has(const struct buf *b, const char *needle)
{
    size_t n = strlen(needle), i;

    if (b->data == NULL || n > b->len)
        return 0;
    for (i = 0; i + n <= b->len; i++)
        if (memcmp(b->data + i, needle, n) == 0)
            return 1;
    return 0;
}

static struct buf slurp_fd(int fd)
{
    struct buf b = { NULL, 0 };
    size_t cap = 0;
    ssize_t n;

    for (;;) {
        if (b.len + 4096 + 1 > cap) {
            cap = cap ? cap * 2 : 8192;
            b.data = realloc(b.data, cap);
            if (b.data == NULL) {
                perror("realloc");
                exit(2);
            }
        }
        n = read(fd, b.data + b.len, cap - b.len - 1);
        if (n < 0 && errno == EINTR)
            continue;
        if (n <= 0)
            break;
        b.len += (size_t)n;
    }
    if (b.data != NULL)
        b.data[b.len] = '\0';
    return b;
}

static struct buf slurp(const char *path)
{
    struct buf b = { NULL, 0 };
    int fd = open(path, O_RDONLY);

    if (fd < 0)
        return b;
    b = slurp_fd(fd);
    close(fd);
    return b;
}

static void write_file(const char *path, const char *content, mode_t mode)
{
    size_t len = strlen(content), off = 0;
    int fd = open(path, O_WRONLY | O_CREAT | O_TRUNC, 0600);

    if (fd < 0) {
        fprintf(stderr, "open(%s): %s\n", path, strerror(errno));
        exit(2);
    }
    while (off < len) {
        ssize_t n = write(fd, content + off, len - off);
        if (n < 0 && errno == EINTR)
            continue;
        if (n <= 0) {
            fprintf(stderr, "write(%s): %s\n", path, strerror(errno));
            exit(2);
        }
        off += (size_t)n;
    }
    close(fd);
    /* Some file systems (HMDFS) ignore or widen the mode: callers that
     * depend on the resulting bits stat() the file afterwards. */
    (void)chmod(path, mode);
}

static void make_dir(const char *path)
{
    if (mkdir(path, 0755) != 0 && errno != EEXIST) {
        fprintf(stderr, "mkdir(%s): %s\n", path, strerror(errno));
        exit(2);
    }
}

/* Remove the plain files of a directory (spool, TMPDIR). */
static void clear_dir(const char *path)
{
    DIR *d = opendir(path);
    struct dirent *e;
    char f[PATH_MAX];

    if (d == NULL)
        return;
    while ((e = readdir(d)) != NULL) {
        if (strcmp(e->d_name, ".") == 0 || strcmp(e->d_name, "..") == 0)
            continue;
        snprintf(f, sizeof(f), "%s/%s", path, e->d_name);
        unlink(f);
    }
    closedir(d);
}

/* Collect the messages the sendmail stand-in delivered. */
static int read_spool(struct buf mails[MAX_MAILS])
{
    DIR *d = opendir(spooldir);
    struct dirent *e;
    char f[PATH_MAX];
    int n = 0;

    if (d == NULL)
        return 0;
    while ((e = readdir(d)) != NULL && n < MAX_MAILS) {
        if (strncmp(e->d_name, "mail-", 5) != 0)
            continue;
        snprintf(f, sizeof(f), "%s/%s", spooldir, e->d_name);
        mails[n++] = slurp(f);
    }
    closedir(d);
    return n;
}

/* Find "<prefix>*" in TMPDIR and return its content. */
static struct buf kept_log(const char *prefix)
{
    struct buf b = { NULL, 0 };
    DIR *d = opendir(tmpdir);
    struct dirent *e;
    char f[PATH_MAX];

    if (d == NULL)
        return b;
    while ((e = readdir(d)) != NULL) {
        if (strncmp(e->d_name, prefix, strlen(prefix)) == 0) {
            snprintf(f, sizeof(f), "%s/%s", tmpdir, e->d_name);
            b = slurp(f);
            break;
        }
    }
    closedir(d);
    return b;
}

static double now(void)
{
    struct timespec ts;

    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
}

/*
 * Run the packaged shush with stdin=/dev/null, stdout/stderr captured, and
 * TMPDIR / SHUSH_TEST_SPOOL / SHUSH_SENDMAIL set for it.  A run that exceeds
 * `limit` seconds is killed (shush ignores SIGTERM by design).
 */
static void run_shush(struct result *r, const char *tag, const char *sendmail_env,
                      int limit, ...)
{
    char *argv[16], outp[PATH_MAX], errp[PATH_MAX];
    const char *arg;
    int argc = 0, status = 0, fd;
    double t0;
    pid_t pid, w;
    va_list ap;

    argv[argc++] = (char *)shush;
    va_start(ap, limit);
    while ((arg = va_arg(ap, const char *)) != NULL && argc < 15)
        argv[argc++] = (char *)arg;
    va_end(ap);
    argv[argc] = NULL;

    snprintf(outp, sizeof(outp), "%s/%s.out", logdir, tag);
    snprintf(errp, sizeof(errp), "%s/%s.err", logdir, tag);
    fflush(stdout);
    t0 = now();
    pid = fork();
    if (pid < 0) {
        perror("fork");
        exit(2);
    }
    if (pid == 0) {
        fd = open("/dev/null", O_RDONLY);
        if (fd >= 0) {
            dup2(fd, 0);
            close(fd);
        }
        fd = open(outp, O_WRONLY | O_CREAT | O_TRUNC, 0644);
        if (fd >= 0) {
            dup2(fd, 1);
            close(fd);
        }
        fd = open(errp, O_WRONLY | O_CREAT | O_TRUNC, 0644);
        if (fd >= 0) {
            dup2(fd, 2);
            close(fd);
        }
        setenv("TMPDIR", tmpdir, 1);
        setenv("SHUSH_TEST_SPOOL", spooldir, 1);
        if (sendmail_env != NULL)
            setenv("SHUSH_SENDMAIL", sendmail_env, 1);
        else
            unsetenv("SHUSH_SENDMAIL");
        execv(shush, argv);
        fprintf(stderr, "test_shush: execv(%s): %s\n", shush, strerror(errno));
        _exit(127);
    }
    for (;;) {
        w = waitpid(pid, &status, WNOHANG);
        if (w == pid)
            break;
        if (w < 0 && errno != EINTR) {
            status = 0xff00;
            break;
        }
        if (now() - t0 > limit) {
            kill(pid, SIGKILL);
            waitpid(pid, &status, 0);
            break;
        }
        {
            struct timespec pause = { 0, 50000000L };
            nanosleep(&pause, NULL);
        }
    }
    r->secs = now() - t0;
    if (WIFEXITED(status))
        r->rc = WEXITSTATUS(status);
    else if (WIFSIGNALED(status))
        r->rc = 128 + WTERMSIG(status);
    else
        r->rc = -1;
    r->out = slurp(outp);
    r->err = slurp(errp);
    printf("  (%s: shush exit %d after %.1fs)\n", tag, r->rc, r->secs);
}

static void show_stderr(const struct result *r)
{
    if (r->err.len > 0)
        printf("  --- shush stderr ---\n%.*s\n  --- end ---\n",
               (int)r->err.len, r->err.data);
}

/* ------------------------------------------------------------------ */

static void case_version(void)
{
    struct result r;

    run_shush(&r, "C1", NULL, 30, "-V", (char *)NULL);
    check("C1", r.rc == 0 && has(&r.out, "(PCRE version 10."),
          "-V reports a PCRE2 (10.x) runtime: exit=%d out=%.*s", r.rc,
          (int)r.out.len, r.out.data ? r.out.data : "");
}

static void write_report_config(mode_t mode)
{
    char path[PATH_MAX], text[2048];

    snprintf(path, sizeof(path), "%s/report", cfgdir);
    snprintf(text, sizeof(text),
             "command=%s job report\n"
             "sendmail=%s\n"
             "format=html\n"
             "subject=[%%n] consumer\n"
             "[ops]\n"
             "to=ops@example.org\n"
             "if=$exit == 3 && E == 1 && I == 1 && W == 1 && $outlines == 3\n"
             "[never]\n"
             "to=nobody@example.org\n"
             "if=$exit == 0\n",
             helper, helper);
    write_file(path, text, mode);
    /* PCRE2-only syntax: inline (?i), \s and \d are not POSIX ERE. */
    snprintf(path, sizeof(path), "%s/report.stdout", cfgdir);
    write_file(path, "#pcre\nE(?i)^error\\s+(\\d+)\\s\nI^info:\n", 0644);
    /* Standard (POSIX ERE, libc regcomp) rules. */
    snprintf(path, sizeof(path), "%s/report.stderr", cfgdir);
    write_file(path, "W^(warn):\n", 0644);
}

static void case_report(void)
{
    struct buf mails[MAX_MAILS];
    struct result r;
    int n, ok;

    clear_dir(spooldir);
    clear_dir(tmpdir);
    write_report_config(0644);
    /* Default syslog facility on purpose: HarmonyOS has no syslogd. */
    run_shush(&r, "C2", NULL, 60, "-c", cfgdir, "report", (char *)NULL);
    n = read_spool(mails);
    ok = r.rc == 0 && n == 1
        && has(&mails[0], "X-Test-Argv: -t -i\n")
        && has(&mails[0], "\nTo: ops@example.org\n")
        && has(&mails[0], "\nSubject: [report] consumer\n")
        && has(&mails[0], "\nX-Shush-Report-Name: ops\n")
        && has(&mails[0], "\nX-Shush-Exit-Status: 3\n")
        && has(&mails[0], "\nContent-Type: text/html\n")
        && has(&mails[0], "ERROR <b>42</b> disk quota")
        && has(&mails[0], "<b>warn</b>: low battery");
    check("C2", ok,
          "report flow: PCRE2 + POSIX counters drive if=, one HTML report via "
          "sendmail -t -i, capture groups in bold (exit=%d mails=%d)", r.rc, n);
    if (!ok) {
        show_stderr(&r);
        if (n > 0)
            printf("  --- mail ---\n%.*s\n  --- end ---\n",
                   (int)mails[0].len, mails[0].data);
    }
}

static void case_kept_logs(void)
{
    struct result r;
    struct buf out, err;
    int ok;

    clear_dir(spooldir);
    clear_dir(tmpdir);
    write_report_config(0644);
    run_shush(&r, "C3", NULL, 60, "-c", cfgdir, "-S", "-k", "report", (char *)NULL);
    out = kept_log("shush-report.stdout.");
    err = kept_log("shush-report.stderr.");
    ok = r.rc == 0 && has(&out, "ERROR 42 disk quota\n")
        && has(&out, "info: done\n") && has(&err, "warn: low battery\n");
    check("C3", ok,
          "-k keeps the command output logs in $TMPDIR (/tmp is read-only "
          "on HarmonyOS): exit=%d stdout-log=%zu B stderr-log=%zu B",
          r.rc, out.len, err.len);
    if (!ok)
        show_stderr(&r);
}

static void write_env_config(void)
{
    char path[PATH_MAX], text[1024];

    /* No "sendmail" parameter: the transport comes from the environment. */
    snprintf(path, sizeof(path), "%s/envmail", cfgdir);
    snprintf(text, sizeof(text),
             "command=%s job quiet\n"
             "subject=[%%n] env transport\n"
             "[all]\n"
             "to=env@example.org\n",
             helper);
    write_file(path, text, 0644);
}

static void case_env_sendmail(void)
{
    struct buf mails[MAX_MAILS];
    struct result r;
    int n, ok;

    clear_dir(spooldir);
    write_env_config();
    run_shush(&r, "C4", helper, 60, "-c", cfgdir, "-S", "envmail", (char *)NULL);
    n = read_spool(mails);
    ok = r.rc == 0 && n == 1
        && has(&mails[0], "\nTo: env@example.org\n")
        && has(&mails[0], "\nX-Shush-Exit-Status: 0\n")
        && has(&mails[0], "all good\n");
    check("C4", ok,
          "SHUSH_SENDMAIL selects the transport when the configuration has "
          "none (exit=%d mails=%d)", r.rc, n);
    if (!ok)
        show_stderr(&r);
}

static void case_default_transport(void)
{
    struct buf mails[MAX_MAILS];
    struct result r;
    int n, ok;

    clear_dir(spooldir);
    write_env_config();
    /* Upstream exec() failure path sleeps 5 s before aborting. */
    run_shush(&r, "C5", NULL, 60, "-c", cfgdir, "-S", "envmail", (char *)NULL);
    n = read_spool(mails);
    /* The execv() diagnostic names the compiled-in default: NOSENDMAIL,
     * not a sendmail path probed on the build machine. */
    ok = n == 0 && has(&r.err, "execv(NOSENDMAIL)");
    check("C5", ok,
          "without a transport shush falls back to the compiled-in "
          "NOSENDMAIL and says so (exit=%d mails=%d)", r.rc, n);
    if (!ok)
        show_stderr(&r);
}

static void case_timeout_signal(void)
{
    struct buf mails[MAX_MAILS];
    struct result r;
    char path[PATH_MAX], text[1024];
    int n, ok;

    clear_dir(spooldir);
    snprintf(path, sizeof(path), "%s/slow", cfgdir);
    snprintf(text, sizeof(text),
             "command=%s job sleep\n"
             "sendmail=%s\n"
             "timeout=2s,SIGTERM\n"
             "[killed]\n"
             "to=ops@example.org\n"
             "if=$exit == -15\n",
             helper, helper);
    write_file(path, text, 0644);
    run_shush(&r, "C6", NULL, 60, "-c", cfgdir, "-S", "slow", (char *)NULL);
    n = read_spool(mails);
    ok = r.rc == 0 && r.secs < 30.0 && n == 1
        && has(&mails[0], "\nX-Shush-Report-Name: killed\n")
        && has(&mails[0], "started\n") && !has(&mails[0], "not killed")
        && !has(&r.err, "Invalid \"timeout\" signal");
    check("C6", ok,
          "timeout=2s,SIGTERM resolves TERM from the target signal table and "
          "stops the job ($exit == -15) after %.1fs (mails=%d)", r.secs, n);
    if (!ok)
        show_stderr(&r);
}

static void case_permissions(void)
{
    struct buf mails[MAX_MAILS];
    struct result r;
    struct stat st;
    char path[PATH_MAX];
    int n, ok;

    snprintf(path, sizeof(path), "%s/report", cfgdir);

    /* Group writable: HMDFS forces this bit on every file. */
    clear_dir(spooldir);
    write_report_config(0664);
    if (stat(path, &st) == 0 && (st.st_mode & S_IWGRP) != 0
        && (st.st_mode & S_IWOTH) == 0) {
        run_shush(&r, "C7a", NULL, 60, "-c", cfgdir, "-S", "report", (char *)NULL);
        n = read_spool(mails);
        ok = r.rc == 0 && n == 1 && !has(&r.err, "writable")
            && !has(&r.err, "someone else owns");
        check("C7a", ok,
              "group writable configuration (mode %04o, uid %u, euid %u) is "
              "accepted and runs (exit=%d mails=%d)",
              (unsigned)(st.st_mode & 07777), (unsigned)st.st_uid,
              (unsigned)geteuid(), r.rc, n);
        if (!ok)
            show_stderr(&r);
    } else {
        notrun++;
        printf("NOT RUN [C7a] could not obtain a group writable, not world "
               "writable file (mode %04o)\n", (unsigned)(st.st_mode & 07777));
    }

    /* World writable: must still be refused. */
    clear_dir(spooldir);
    write_report_config(0666);
    if (stat(path, &st) == 0 && (st.st_mode & S_IWOTH) != 0) {
        run_shush(&r, "C7b", NULL, 60, "-c", cfgdir, "-S", "report", (char *)NULL);
        n = read_spool(mails);
        ok = r.rc == 1 && n == 0 && has(&r.err, "must not be world writable");
        check("C7b", ok,
              "world writable configuration (mode %04o) is refused "
              "(exit=%d mails=%d)", (unsigned)(st.st_mode & 07777), r.rc, n);
        if (!ok)
            show_stderr(&r);
    } else {
        notrun++;
        printf("NOT RUN [C7b] file system did not keep o+w (mode %04o): the "
               "refusal path cannot be constructed here\n",
               (unsigned)(st.st_mode & 07777));
    }
    write_report_config(0644);
}

static void case_crontab(void)
{
    struct result r;
    char path[PATH_MAX], text[1024];
    int ok;

    snprintf(path, sizeof(path), "%s/nightly", crondir);
    snprintf(text, sizeof(text),
             "command=%s job quiet\n"
             "schedule=0 3 * * *\n",
             helper);
    write_file(path, text, 0644);
    /* No crontab(1)/crond on HarmonyOS PC: CRONTAB is pinned to NOCRONTAB,
     * and OHOS musl's tmpfile() uses /data/local/tmp. */
    run_shush(&r, "C8", NULL, 60, "-c", crondir, "-u", (char *)NULL);
    ok = r.rc == 1 && r.secs < 30.0
        && (has(&r.err, "NOCRONTAB") || has(&r.err, "temporary file"));
    check("C8", ok,
          "-u (crontab update) fails cleanly with a diagnostic because "
          "HarmonyOS PC has no crontab (exit=%d after %.1fs)", r.rc, r.secs);
    show_stderr(&r);
}

static int driver(const char *workdir)
{
    make_dir(workdir);
    snprintf(cfgdir, sizeof(cfgdir), "%s/cfg", workdir);
    snprintf(crondir, sizeof(crondir), "%s/cron", workdir);
    snprintf(spooldir, sizeof(spooldir), "%s/spool", workdir);
    snprintf(tmpdir, sizeof(tmpdir), "%s/tmp", workdir);
    snprintf(logdir, sizeof(logdir), "%s/logs", workdir);
    make_dir(cfgdir);
    make_dir(crondir);
    make_dir(spooldir);
    make_dir(tmpdir);
    make_dir(logdir);

    case_version();
    case_report();
    case_kept_logs();
    case_env_sendmail();
    case_default_transport();
    case_timeout_signal();
    case_permissions();
    case_crontab();

    printf("shush consumer test: passed=%d failed=%d notrun=%d\n",
           passed, failed, notrun);
    return (failed == 0 && passed > 0) ? 0 : 1;
}

/* sendmail stand-in: "<helper> -t -i", message on stdin. */
static int mailer(int argc, char **argv)
{
    const char *spool = getenv("SHUSH_TEST_SPOOL");
    char part[PATH_MAX], done[PATH_MAX];
    struct buf msg;
    FILE *f;
    int i;

    if (spool == NULL) {
        fprintf(stderr, "test_shush: SHUSH_TEST_SPOOL is not set\n");
        return 75;
    }
    msg = slurp_fd(0);
    snprintf(part, sizeof(part), "%s/.part-%ld", spool, (long)getpid());
    snprintf(done, sizeof(done), "%s/mail-%ld", spool, (long)getpid());
    f = fopen(part, "w");
    if (f == NULL) {
        fprintf(stderr, "test_shush: %s: %s\n", part, strerror(errno));
        return 75;
    }
    fprintf(f, "X-Test-Argv:");
    for (i = 1; i < argc; i++)
        fprintf(f, " %s", argv[i]);
    fprintf(f, "\n");
    if (msg.len > 0)
        fwrite(msg.data, 1, msg.len, f);
    if (fclose(f) != 0 || rename(part, done) != 0) {
        fprintf(stderr, "test_shush: cannot store %s: %s\n", done, strerror(errno));
        return 75;
    }
    return 0;
}

/* The supervised command. */
static int job(const char *mode)
{
    if (strcmp(mode, "report") == 0) {
        printf("consumer step 1 ok\n");
        printf("ERROR 42 disk quota\n");
        printf("info: done\n");
        fflush(stdout);
        fprintf(stderr, "warn: low battery\n");
        return 3;
    }
    if (strcmp(mode, "quiet") == 0) {
        printf("all good\n");
        return 0;
    }
    if (strcmp(mode, "sleep") == 0) {
        printf("started\n");
        fflush(stdout);
        sleep(60);
        printf("not killed\n");
        return 0;
    }
    fprintf(stderr, "test_shush: unknown job mode %s\n", mode);
    return 64;
}

int main(int argc, char **argv)
{
    if (argc >= 2 && strcmp(argv[1], "-t") == 0)
        return mailer(argc, argv);
    if (argc == 3 && strcmp(argv[1], "job") == 0)
        return job(argv[2]);
    if (argc == 5 && strcmp(argv[1], "run") == 0) {
        shush = argv[2];
        helper = argv[3];
        return driver(argv[4]);
    }
    fprintf(stderr,
            "usage: %s run <shush> <helper> <workdir> | -t -i | job <mode>\n",
            argv[0]);
    return 64;
}
