#include <notcurses/notcurses.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>
#include <unistd.h>
#include <fcntl.h>
#include <errno.h>
#include <pty.h>
#include <time.h>
#include <sys/ioctl.h>

/* R34/R40: this test must exercise the real library, not just print strings.
 *
 * 1. notcurses_version() API + version-string check
 * 2. pty-based functional cycle (no real terminal needed):
 *    - open a pty and hand the slave end to notcurses as its terminal
 *    - notcurses_init(): terminal setup, input thread startup, initial
 *      queries (skipped/bounded on terminals that never answer)
 *    - render a plane with text
 *    - inject a 'q' keypress via the pty master and read it back through
 *      the notcurses input layer (input thread -> queue -> get_nblock)
 *    - notcurses_stop(): cooperative input-thread shutdown must return
 *      (a deadlock or a leaked detached thread would hang/fail here)
 */

static int test_version(void) {
    const char *ver = notcurses_version();
    if (ver == NULL) {
        fprintf(stderr, "FAIL: notcurses_version() returned NULL\n");
        return 1;
    }
    printf("notcurses version: %s\n", ver);
    if (strstr(ver, "3.0") == NULL) {
        fprintf(stderr, "FAIL: unexpected version %s\n", ver);
        return 1;
    }
    return 0;
}

static int test_pty_cycle(void) {
    int mfd = -1, sfd = -1;
    if (openpty(&mfd, &sfd, NULL, NULL, NULL)) {
        fprintf(stderr, "FAIL: openpty: %s\n", strerror(errno));
        return 1;
    }
    /* a fresh pty reports a 0x0 window size, which notcurses rejects */
    struct winsize ws = { .ws_row = 24, .ws_col = 80 };
    if (ioctl(sfd, TIOCSWINSZ, &ws)) {
        fprintf(stderr, "FAIL: TIOCSWINSZ: %s\n", strerror(errno));
        close(mfd); close(sfd);
        return 1;
    }
    /* notcurses needs terminfo; TERMINFO is injected by the test conanfile
     * (pointing into the ncurses package). A missing entry is a hard error
     * for init, so fail loudly instead of skipping. */
    const char *terminfo = getenv("TERMINFO");
    if (terminfo == NULL || access(terminfo, F_OK) != 0) {
        fprintf(stderr, "FAIL: TERMINFO not set or missing: %s\n",
                terminfo ? terminfo : "(unset)");
        close(mfd); close(sfd);
        return 1;
    }
    setenv("TERM", "xterm-256color", 1);

    /* the notcurses input layer always reads the process stdin (fd 0);
     * wire the pty slave in as stdin before initializing */
    if (dup2(sfd, STDIN_FILENO) < 0) {
        fprintf(stderr, "FAIL: dup2 stdin: %s\n", strerror(errno));
        close(mfd); close(sfd);
        return 1;
    }

    FILE *out = fdopen(sfd, "w");
    if (out == NULL) {
        fprintf(stderr, "FAIL: fdopen: %s\n", strerror(errno));
        close(mfd); close(sfd);
        return 1;
    }
    notcurses_options nopts = {0};
    struct notcurses *nc = notcurses_init(&nopts, out);
    if (nc == NULL) {
        fprintf(stderr, "FAIL: notcurses_init() returned NULL\n");
        fclose(out); close(mfd);
        return 1;
    }
    printf("notcurses_init: OK\n");

    struct ncplane *n = notcurses_stdplane(nc);
    if (ncplane_set_fg_rgb8(n, 0x20, 0x80, 0xff)) {
        fprintf(stderr, "FAIL: ncplane_set_fg_rgb8\n");
        notcurses_stop(nc);
        fclose(out); close(mfd);
        return 1;
    }
    if (ncplane_putstr_yx(n, 0, 0, "notcurses pty smoke test") < 0) {
        fprintf(stderr, "FAIL: ncplane_putstr_yx\n");
        notcurses_stop(nc);
        fclose(out); close(mfd);
        return 1;
    }
    if (notcurses_render(nc)) {
        fprintf(stderr, "FAIL: notcurses_render()\n");
        notcurses_stop(nc);
        fclose(out); close(mfd);
        return 1;
    }
    printf("notcurses_render: OK\n");

    /* inject a keypress: the input thread (polling the slave) must pick it
     * up, run it through the automaton and deliver it via the input queue */
    if (write(mfd, "q", 1) != 1) {
        fprintf(stderr, "FAIL: write to pty master: %s\n", strerror(errno));
        notcurses_stop(nc);
        fclose(out); close(mfd);
        return 1;
    }
    ncinput ni;
    uint32_t key = 0;
    struct timespec deadline;
    clock_gettime(CLOCK_MONOTONIC, &deadline);
    deadline.tv_sec += 10; /* generous bound; healthy path is <100ms */
    for (;;) {
        key = notcurses_get_nblock(nc, &ni);
        if (key == 'q') {
            break;
        }
        if (key == (uint32_t)-1) {
            fprintf(stderr, "FAIL: input error\n");
            notcurses_stop(nc);
            fclose(out); close(mfd);
            return 1;
        }
        struct timespec now;
        clock_gettime(CLOCK_MONOTONIC, &now);
        if (now.tv_sec > deadline.tv_sec ||
            (now.tv_sec == deadline.tv_sec && now.tv_nsec >= deadline.tv_nsec)) {
            fprintf(stderr, "FAIL: no keypress delivered within 10s "
                    "(input layer broken?)\n");
            notcurses_stop(nc);
            fclose(out); close(mfd);
            return 1;
        }
        struct timespec nap = { .tv_sec = 0, .tv_nsec = 10 * 1000 * 1000, };
        nanosleep(&nap, NULL);
    }
    printf("input layer delivered 'q': OK\n");

    /* teardown: exercises stop_inputlayer (cooperative input-thread join,
     * free_inputctx, fd state restore). a deadlock here hangs the test. */
    if (notcurses_stop(nc)) {
        fprintf(stderr, "FAIL: notcurses_stop() returned error\n");
        fclose(out); close(mfd);
        return 1;
    }
    printf("notcurses_stop: OK\n");
    fclose(out);
    close(mfd);
    return 0;
}

int main(void) {
    if (test_version()) {
        return 1;
    }
    if (test_pty_cycle()) {
        return 1;
    }
    printf("test notcurses 3.0.17: OK\n");
    return 0;
}
