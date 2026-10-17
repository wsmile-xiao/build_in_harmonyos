/*
 * test_runner.c — consumer-side validation for kirigami-gallery 26.04.0
 * on HarmonyOS PC.
 *
 * Executes the packaged kirigami2gallery binary headlessly (the conanfile
 * sets QT_QPA_PLATFORM=offscreen and the QML import paths) and checks the
 * full QML stack really loads:
 *
 *   - src/main.cpp returns -1 (255 as exit status) when
 *     engine.rootObjects().isEmpty()  -> QML load failure  -> this test FAILS
 *   - QML loads -> app.exec() blocks in the event loop
 *     -> still running after 8 s -> SIGTERM the child -> PASS
 *   - any other exit within the window -> FAIL (unexpected)
 *
 * POSIX only (unistd.h/sys/wait.h/signal.h): no OHOS-specific APIs.
 */
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/wait.h>
#include <unistd.h>

#define WATCH_SECONDS 8
#define POLL_STEPS (WATCH_SECONDS * 10) /* 100 ms per step */
#define TERM_WAIT_STEPS 30              /* 3 s grace after SIGTERM */

int main(int argc, char **argv)
{
    if (argc < 2) {
        fprintf(stderr, "usage: %s <path-to-kirigami2gallery>\n", argv[0]);
        return 2;
    }

    pid_t pid = fork();
    if (pid < 0) {
        perror("fork");
        return 2;
    }
    if (pid == 0) {
        execl(argv[1], argv[1], (char *)NULL);
        perror("execl");
        _exit(127);
    }

    for (int i = 0; i < POLL_STEPS; i++) {
        int status = 0;
        pid_t r = waitpid(pid, &status, WNOHANG);
        if (r == pid) {
            if (WIFEXITED(status) && WEXITSTATUS(status) == 255) {
                fprintf(stderr,
                        "FAIL: kirigami2gallery exited 255: QML engine failed "
                        "to load (rootObjects empty)\n");
                return 1;
            }
            if (WIFEXITED(status)) {
                fprintf(stderr, "FAIL: app exited unexpectedly (code %d)\n",
                        WEXITSTATUS(status));
            } else if (WIFSIGNALED(status)) {
                fprintf(stderr, "FAIL: app crashed (signal %d)\n",
                        WTERMSIG(status));
            }
            return 1;
        }
        usleep(100 * 1000);
    }

    /* Still alive after 8 s: QML UI loaded, event loop is running. */
    kill(pid, SIGTERM);
    for (int i = 0; i < TERM_WAIT_STEPS; i++) {
        int status = 0;
        if (waitpid(pid, &status, WNOHANG) == pid)
            break;
        usleep(100 * 1000);
    }
    printf("PASS: kirigami2gallery QML UI loaded and event loop alive for "
           "%d s (headless)\n", WATCH_SECONDS);
    return 0;
}
