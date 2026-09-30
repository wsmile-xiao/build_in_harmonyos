/* test_litexl.c — substantive smoke test for the lite-xl package (lite 2.1.8).
 *
 * R34: this test GENUINELY executes the packaged lite-xl binary and verifies
 * real runtime behavior — it does not just print a string.
 *
 * IMPORTANT (source-verified): lite-xl 2.1.8 has NO `--command` CLI option
 * (src/main.c does not parse any CLI flags; all argv entries land in the ARGS
 * table as file paths), and core.log() only writes into the internal
 * log_items / status view — it never goes to stdout.  So the old
 * `--command "core.log(...)"` approach can never work.
 *
 * This test instead walks lite-xl's REAL startup path:
 *   main.c: SDL_Init → create window → init renderer → boot embedded Lua VM
 *     → core.init() → core.load_user_directory()
 *     → dofile($LITE_USERDIR/init.lua)
 * We create a temporary USERDIR (via the LITE_USERDIR env var that
 * data/core/start.lua honors) containing an init.lua that prints a marker
 * and calls os.exit(0).  The whole chain (SDL / renderer / Lua VM / core
 * modules / user config) executes before the clean exit.
 *
 * Failure modes caught: binary missing, dependency .so not loadable, SDL or
 * renderer init failure, init.lua never reached → non-zero exit or missing
 * marker → FAIL.  A 60s timeout guards against a hung event loop.
 */
#include <errno.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#define MARKER "LITE_XL_TEST_OK"
#define TIMEOUT_MS 60000
#define OUT_BUF 8192

static int failures = 0;

static void fail(const char *msg)
{
    fprintf(stderr, "[FAIL] %s\n", msg);
    ++failures;
}

int main(void)
{
    const char *bin = getenv("LITE_XL_BIN");
    if (!bin || !*bin)
        bin = "lite-xl";

    /* ---- 1. prepare a temp USERDIR containing init.lua ----
     * lite-xl's core.load_user_directory() dofiles $LITE_USERDIR/init.lua
     * during startup.  Ours prints the marker to stdout and exits 0. */
    char userdir[512];
    snprintf(userdir, sizeof(userdir), "litexl_test_user_%ld", (long)getpid());
    if (mkdir(userdir, 0755) != 0) {
        perror("mkdir");
        return 1;
    }
    char initpath[1024];
    snprintf(initpath, sizeof(initpath), "%s/init.lua", userdir);
    FILE *fp = fopen(initpath, "w");
    if (!fp) {
        perror("fopen init.lua");
        rmdir(userdir);
        return 1;
    }
    fprintf(fp, "print(\"%s\")\n", MARKER);
    fprintf(fp, "os.exit(0)\n");
    fclose(fp);

    /* ---- 2. fork/exec the real lite-xl binary headless ----
     * LITE_USERDIR: point lite-xl at our temp user config dir.
     * SDL dummy drivers: run without a display server. */
    int pipefd[2];
    if (pipe(pipefd) != 0) {
        perror("pipe");
        remove(initpath);
        rmdir(userdir);
        return 1;
    }

    pid_t pid = fork();
    if (pid < 0) {
        perror("fork");
        remove(initpath);
        rmdir(userdir);
        return 1;
    }

    if (pid == 0) {
        /* child: exec the real binary headless */
        dup2(pipefd[1], STDOUT_FILENO);
        dup2(pipefd[1], STDERR_FILENO);
        close(pipefd[0]);
        close(pipefd[1]);
        setenv("SDL_VIDEODRIVER", "dummy", 1);
        setenv("SDL_AUDIODRIVER", "dummy", 1);
        setenv("LITE_USERDIR", userdir, 1);
        execl(bin, bin, (char *)NULL);
        fprintf(stderr, "[FAIL] execl '%s': %s\n", bin, strerror(errno));
        _exit(127);
    }

    close(pipefd[1]);

    /* ---- 3. parent: read child output with timeout ---- */
    char buf[OUT_BUF];
    size_t n = 0;
    struct pollfd pfd = { .fd = pipefd[0], .events = POLLIN };
    int timed_out = 0;
    int full = 0;
    for (;;) {
        int r = poll(&pfd, 1, TIMEOUT_MS);
        if (r == 0) {
            timed_out = 1;
            break;
        }
        if (r < 0) {
            if (errno == EINTR)
                continue;
            perror("poll");
            break;
        }
        ssize_t k = read(pipefd[0], buf + n, sizeof(buf) - 1 - n);
        if (k == 0)
            break; /* EOF: child closed stdout */
        if (k < 0) {
            if (errno == EINTR)
                continue;
            perror("read");
            break;
        }
        n += (size_t)k;
        if (n >= sizeof(buf) - 1) {
            full = 1;
            break;
        }
    }
    buf[n] = '\0';
    close(pipefd[0]);

    int status = 0;
    if (timed_out || full) {
        /* didn't see EOF → child still running (hung or wrote too much) */
        kill(pid, SIGKILL);
        waitpid(pid, &status, 0);
        if (timed_out)
            fail("lite-xl timed out (60s) without exiting");
        else
            fail("lite-xl output exceeded buffer without exiting");
    } else {
        /* EOF reached: child closed stdout; give it a moment to reap */
        int done = 0;
        for (int i = 0; i < 50; i++) {
            pid_t r = waitpid(pid, &status, WNOHANG);
            if (r == pid) {
                done = 1;
                break;
            }
            if (r < 0) {
                perror("waitpid");
                remove(initpath);
                rmdir(userdir);
                return 1;
            }
            usleep(100000); /* 100ms */
        }
        if (!done) {
            kill(pid, SIGKILL);
            waitpid(pid, &status, 0);
            fail("lite-xl closed stdout but did not exit");
        }
    }

    printf("--- lite-xl output (%u bytes) ---\n%.*s\n-------------------------------\n",
           (unsigned)n, (int)n, buf);

    if (!timed_out && !full) {
        if (WIFEXITED(status) && WEXITSTATUS(status) == 0) {
            printf("[ok] lite-xl exited 0\n");
        } else {
            fprintf(stderr, "[FAIL] lite-xl exit status: %s%d%s%s\n",
                    WIFEXITED(status) ? "code " : "signal ",
                    WIFEXITED(status) ? WEXITSTATUS(status) : WTERMSIG(status),
                    WIFSIGNALED(status) ? " (" : "",
                    WIFSIGNALED(status) ? strsignal(WTERMSIG(status)) : "");
            ++failures;
        }
        if (strstr(buf, MARKER)) {
            printf("[ok] lite-xl Lua runtime printed '%s'\n", MARKER);
        } else {
            fprintf(stderr, "[FAIL] marker '%s' not found in lite-xl output\n", MARKER);
            ++failures;
        }
    }

    /* ---- 4. cleanup temp userdir ---- */
    remove(initpath);
    rmdir(userdir);

    if (failures) {
        fprintf(stderr, "test_litexl: %d assertion(s) failed\n", failures);
        return 1;
    }
    printf("test_litexl: all assertions passed (lite-xl binary + Lua API OK)\n");
    return 0;
}
