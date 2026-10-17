/*
 * Consumer-side test for libfuse 3.16.1 on OpenHarmony (aarch64).
 *
 * The OHOS user space has no /dev/fuse, so a real filesystem cannot be
 * mounted.  The test therefore exercises everything that does not need a
 * mounted filesystem, but it does drive the two code paths that this port
 * had to rework because OHOS' libc has no POSIX thread cancellation:
 *
 *   1. the LRU node cleanup thread (fuse_start_cleanup_thread /
 *      fuse_stop_cleanup_thread) - lib/fuse.c
 *   2. the multi-threaded session loop (fuse_session_loop_mt) - lib/fuse_loop_mt.c
 *
 * Both must terminate on their own; a regression in the replacement of
 * pthread_cancel() shows up here as a hang or as a failed assertion.
 */
#define FUSE_USE_VERSION 312

#include <errno.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>

#include <fuse3/fuse.h>
#include <fuse3/fuse_lowlevel.h>
#include <fuse3/fuse_opt.h>

static int failures;

static void check(int ok, const char *what)
{
	printf("%s: %s\n", ok ? "PASS" : "FAIL", what);
	if (!ok)
		failures++;
}

struct test_opts {
	int verbose;
	char *tag;
};

#define TEST_OPT(t, p) { t, offsetof(struct test_opts, p), 1 }

static const struct fuse_opt test_opt_spec[] = {
	TEST_OPT("--tag=%s", tag),
	TEST_OPT("verbose", verbose),
	FUSE_OPT_END
};

static void test_version_and_options(void)
{
	struct fuse_args args = FUSE_ARGS_INIT(0, NULL);
	struct test_opts opts = { 0, NULL };
	int rc;

	/* Version handshake between the built library and these headers. */
	check(fuse_version() == FUSE_VERSION,
	      "fuse_version() matches the headers it was built against");
	check(fuse_version() == 316, "fuse_version() is 316 (libfuse 3.16.1)");

	rc = fuse_opt_add_arg(&args, "test_libfuse");
	check(rc == 0, "fuse_opt_add_arg() accepted the program name");
	rc = fuse_opt_add_arg(&args, "--tag=ohos");
	check(rc == 0, "fuse_opt_add_arg() accepted --tag=ohos");
	rc = fuse_opt_parse(&args, &opts, test_opt_spec, NULL);
	check(rc == 0, "fuse_opt_parse() consumed the custom option table");
	check(opts.tag != NULL && strcmp(opts.tag, "ohos") == 0,
	      "fuse_opt_parse() stored the --tag argument value");
	check(args.argc == 1, "fuse_opt_parse() removed the consumed argument");
	fuse_opt_free_args(&args);
}

/* 1. High-level object lifecycle, including the LRU cleanup thread. */
static void test_cleanup_thread(void)
{
	struct fuse_args args = FUSE_ARGS_INIT(0, NULL);
	struct fuse_operations ops;
	struct fuse *f;
	int rc;

	memset(&ops, 0, sizeof(ops));
	fuse_opt_add_arg(&args, "test_libfuse");
	fuse_opt_add_arg(&args, "-o");
	fuse_opt_add_arg(&args, "remember=1");

	f = fuse_new(&args, &ops, sizeof(ops), NULL);
	check(f != NULL, "fuse_new() created a FUSE object");
	if (f != NULL) {
		rc = fuse_start_cleanup_thread(f);
		check(rc == 0, "fuse_start_cleanup_thread() started the LRU pruner");
		/* Must return: on OHOS the thread leaves through a stop flag
		 * instead of pthread_cancel(). */
		fuse_stop_cleanup_thread(f);
		fuse_destroy(f);
	}
	fuse_opt_free_args(&args);
}

/* 2. Low-level session and the multi-threaded loop. */
static void test_session_loop_mt(void)
{
	static struct fuse_lowlevel_ops llops;
	struct fuse_args args = FUSE_ARGS_INIT(0, NULL);
	struct fuse_session *se;
	int rc;

	fuse_opt_add_arg(&args, "test_libfuse");
	se = fuse_session_new(&args, &llops, sizeof(llops), NULL);
	check(se != NULL, "fuse_session_new() created a low-level session");
	if (se != NULL) {
		/* fuse_session_mount() is deliberately skipped: without a mount
		 * the session has no channel descriptor, so the loop is expected
		 * to report that channel error.  What matters is that it returns -
		 * with pthread_cancel() unavailable the workers are released by
		 * the bounded poll in fuse_do_work(). */
		rc = fuse_session_loop_mt(se, NULL);
		check(rc == -EBADF,
		      "fuse_session_loop_mt() terminated and reported the missing channel");
		fuse_session_destroy(se);
	}
	fuse_opt_free_args(&args);
}

int main(void)
{
	test_version_and_options();
	test_cleanup_thread();
	test_session_loop_mt();

	printf("test libfuse 3.16.1: %s (%d failure(s))\n",
	       failures == 0 ? "PASSED" : "FAILED", failures);
	return failures == 0 ? 0 : 1;
}
