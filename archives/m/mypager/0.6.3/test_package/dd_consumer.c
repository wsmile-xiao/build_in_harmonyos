/*
 * Consumer test for mypager 0.6.3 (Perl pager script).
 *
 *   1. runs "mypager --installconf" against a fresh HOME and asserts
 *      exit 0 plus the config file ($HOME/.mypager.conf) was created —
 *      --installconf is the only documented switch (mypager has no
 *      --help; run argless the script pages stdin until EOF, which
 *      hangs a CI worker whose stdin never closes);
 *   2. pipes a short text file through "mypager" and asserts the
 *      content passes through (a file shorter than one page is not
 *      truncated by the pager).
 */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

static char line[4096];

static int run_capture(const char *script, const char *args, char *buf,
                       size_t buflen) {
    char cmd[2048];
    snprintf(cmd, sizeof cmd, "\"%s\" %s 2>&1", script, args);
    FILE *fp = popen(cmd, "r");
    if (!fp) return -1;
    size_t n = 0;
    while (n + 1 < buflen && fgets(buf + n, (int)(buflen - n), fp)) {
        n = strlen(buf);
    }
    int rc = pclose(fp);
    return (rc < 0) ? -1 : rc;
}

int main(void) {
    const char *script = getenv("MYPAGER_SCRIPT");
    if (!script || script[0] == '\0') {
        fprintf(stderr, "FAIL: MYPAGER_SCRIPT not set\n");
        return 1;
    }

    /* 1. --installconf against a fresh HOME (must not prompt: the config
     *    file cannot pre-exist in a per-run directory) */
    char buf[8192];
    memset(buf, 0, sizeof buf);
    char confhome[1024];
    snprintf(confhome, sizeof confhome, "mypager_confhome_%d", (int)getpid());
    if (mkdir(confhome, 0755) != 0 && errno != EEXIST) {
        perror("FAIL: mkdir confhome");
        return 8;
    }
    setenv("HOME", confhome, 1);
    int rc = run_capture(script, "--installconf", buf, sizeof buf);
    if (rc != 0) {
        fprintf(stderr, "FAIL: mypager --installconf exited %d\noutput:\n%s\n",
                rc, buf);
        return 2;
    }
    char confpath[1200];
    snprintf(confpath, sizeof confpath, "%s/.mypager.conf", confhome);
    struct stat st;
    if (stat(confpath, &st) != 0) {
        fprintf(stderr, "FAIL: --installconf did not create %s\noutput:\n%s\n",
                confpath, buf);
        return 3;
    }

    /* 2. short file through the pager */
    const char *tmp = "/data/tmp/my pager_dd.txt";
    tmp = "/data/tmp/mypager_dd.txt";
    FILE *f = fopen(tmp, "w");
    if (!f) {
        tmp = "mypager_dd_in.txt";
        f = fopen(tmp, "w");
        if (!f) { perror("FAIL: tmp file"); return 4; }
    }
    fputs("line-one-of-consumer-test\nline-two-of-consumer-test\n", f);
    fclose(f);

    memset(buf, 0, sizeof buf);
    char cmd[2048];
    snprintf(cmd, sizeof cmd, "\"%s\" < \"%s\" 2>&1", script, tmp);
    FILE *fp = popen(cmd, "r");
    if (!fp) { perror("FAIL: popen pager"); return 5; }
    size_t n = 0;
    while (n + 1 < sizeof buf && fgets(buf + n, (int)(sizeof buf - n), fp)) {
        n = strlen(buf);
    }
    rc = pclose(fp);
    if (rc != 0) {
        fprintf(stderr, "FAIL: pager exited %d\noutput:\n%s\n", rc, buf);
        return 6;
    }
    if (!strstr(buf, "line-one-of-consumer-test")) {
        fprintf(stderr, "FAIL: pager output lost content\noutput:\n%s\n", buf);
        return 7;
    }

    printf("dd_consumer OK: mypager --installconf and pipe-through verified\n");
    return 0;
}
