/*
 * libuev HarmonyOS PC (aarch64) platform-specific test.
 *
 * Verifies the OHOS-specific adaptation: on the HarmonyOS kernel a signalfd
 * is shared across fork(), so when a forked child dies from a blocked signal
 * the parent's epoll sees a spurious readable event whose read() returns
 * EAGAIN.  libuev must not dispatch a signal callback for that spurious
 * wakeup (uev.c EAGAIN guard).  This test reproduces the exact upstream
 * signal.c scenario and asserts the parent only receives SIGCHLD.
 *
 * Also exercises the basic event loop (timer) on OHOS to confirm the core
 * epoll path works.  Uses only public headers and public API.
 */
#include <stdio.h>
#include <stdlib.h>
#include <sys/wait.h>
#include <unistd.h>

#include <uev/uev.h>

static int child_crash(void)
{
	volatile int *p = (int *)0;
	*p = 42;			/* segfault, SIGSEGV */
	return 42;
}

static void sig_cb(uev_t *w, void *arg, int events)
{
	int *got_sigchld = arg;

	switch (w->signo) {
	case SIGCHLD:
		(*got_sigchld)++;
		printf("[OHOS] got SIGCHLD from pid %d\n", w->siginfo.ssi_pid);
		uev_exit(w->ctx);
		break;
	case SIGSEGV:
		printf("[OHOS] FAIL: spurious SIGSEGV callback (ssi_signo=%d)\n",
		       w->siginfo.ssi_signo);
		uev_exit(w->ctx);
		break;
	default:
		printf("[OHOS] FAIL: unhandled signal %d\n", w->signo);
		uev_exit(w->ctx);
		break;
	}
}

static void timer_cb(uev_t *w, void *arg, int events)
{
	printf("[OHOS] timer fired, event loop alive\n");
}

int main(void)
{
	uev_ctx_t ctx;
	uev_t sigchld, sigsegv, timer;
	int got_sigchld = 0;
	pid_t pid, reaped;
	int rc = 0;

	if (uev_init(&ctx)) {
		fprintf(stderr, "[OHOS] uev_init failed\n");
		return 1;
	}

	if (uev_signal_init(&ctx, &sigsegv, sig_cb, &got_sigchld, SIGSEGV)) {
		fprintf(stderr, "[OHOS] uev_signal_init(SIGSEGV) failed\n");
		return 1;
	}
	if (uev_signal_init(&ctx, &sigchld, sig_cb, &got_sigchld, SIGCHLD)) {
		fprintf(stderr, "[OHOS] uev_signal_init(SIGCHLD) failed\n");
		return 1;
	}
	if (uev_timer_init(&ctx, &timer, timer_cb, NULL, 50, 0)) {
		fprintf(stderr, "[OHOS] uev_timer_init failed\n");
		return 1;
	}

	/* Fork a child that segfaults; parent must see only SIGCHLD. */
	pid = fork();
	if (pid == 0)
		_exit(child_crash());

	reaped = waitpid(pid, &rc, 0);
	printf("[OHOS] child %d reaped, WIFSIGNALED=%d WTERMSIG=%d\n",
	       reaped, WIFSIGNALED(rc), WTERMSIG(rc));

	uev_run(&ctx, 0);

	if (got_sigchld != 1) {
		printf("[OHOS] FAIL: expected exactly 1 SIGCHLD, got %d\n",
		       got_sigchld);
		return 1;
	}

	printf("[OHOS] fork+signalfd EAGAIN adaptation verified: PASS\n");
	return 0;
}
