#include <stdio.h>
#include <unistd.h>
#include <sys/wait.h>

/* Headless GLU/GLEW shim matrix self-test entry point, implemented in the
 * recipe's compat/glu_glew_shim.cpp (AI review PR #9643 follow-up: the
 * self-test used to be linked only by the recipe build() probe; it is now
 * wired into the consumer-side test phase as well). test_package compiles
 * the shim source together with this file, so the matrix maths - the
 * highest-risk part of the GLU shim (invert_matrix Gauss-Jordan + transpose
 * fix, multiply_matrix P*M order, gluProject/gluUnProject round-trip) -
 * regresses fail here too, without any GL context.
 */
extern int glu_glew_shim_selftest(void);

/* Smoke test: run `logstalgia --help` and verify the binary starts and
 * prints help, exiting 0.
 *
 * Why execlp() instead of system(): the OHOS default /system/bin/sh (mksh)
 * cannot exec ELF binaries directly; system("logstalgia --help") would go
 * through mksh and fail. execlp() lets this test program (an ELF itself,
 * launched by bash) exec the target ELF directly. --help does not enter the
 * render loop, so it is safe in headless CI (verified locally: prints the
 * full help text and exits 0 with gl4es initialising against the OHOS
 * system EGL/GLES3 stack).
 */
int main(void) {
    int rc = glu_glew_shim_selftest();
    if (rc != 0) {
        printf("glu_glew_shim_selftest: FAIL (rc=%d)\n", rc);
        return 1;
    }
    printf("glu_glew_shim_selftest: PASS\n");

    pid_t pid = fork();
    if (pid < 0) {
        perror("fork");
        return 1;
    }
    if (pid == 0) {
        execlp("logstalgia", "logstalgia", "--help", (char *)NULL);
        perror("execlp logstalgia");
        _exit(127);
    }
    int status = 0;
    if (waitpid(pid, &status, 0) < 0) {
        perror("waitpid");
        return 1;
    }
    if (WIFEXITED(status) && WEXITSTATUS(status) == 0) {
        printf("logstalgia: help OK\n");
        return 0;
    }
    printf("logstalgia: help failed (status=%d)\n", status);
    return 1;
}
