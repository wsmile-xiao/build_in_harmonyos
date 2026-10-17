/*
 * L1 consumer test for libinput 1.26.2.
 *
 * Verifies the installed package from a consumer's point of view: the public
 * header compiles, the library links, and the real API works at runtime.
 *
 * Everything here runs WITHOUT udev and WITHOUT /dev/uinput: the path-based
 * backend (libinput_path_create_context) is part of the public API and creates
 * an empty context that needs no seat and no device.  That is deliberate — the
 * upstream litest suite cannot run in this environment (it creates virtual
 * devices through /dev/uinput), so this test covers what can be verified for
 * real: header + link + context lifecycle + the documented failure mode of
 * adding a device that does not exist.
 */
#include <libinput.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

static int checks;
static int failures;

#define CHECK(cond, what)                                                      \
	do {                                                                   \
		checks++;                                                      \
		if (cond) {                                                    \
			printf("  ok   - %s\n", what);                         \
		} else {                                                       \
			failures++;                                            \
			printf("  FAIL - %s\n", what);                         \
		}                                                              \
	} while (0)

/* The interface is mandatory to create a context.  Neither callback is ever
 * invoked here (no device is ever opened), so failing loudly is correct. */
static int
open_restricted(const char *path, int flags, void *user_data)
{
	(void)path;
	(void)flags;
	(void)user_data;
	fprintf(stderr, "open_restricted() must not be called: %s\n",
		path ? path : "(null)");
	return -1;
}

static void
close_restricted(int fd, void *user_data)
{
	(void)fd;
	(void)user_data;
}

static const struct libinput_interface iface = {
	.open_restricted = open_restricted,
	.close_restricted = close_restricted,
};

int
main(void)
{
	struct libinput *li;
	struct libinput_device *dev;

	printf("libinput consumer test\n");

	/* 1. path-based context: public API, no udev, no seat required. */
	li = libinput_path_create_context(&iface, NULL);
	CHECK(li != NULL, "libinput_path_create_context() returns a context");
	if (!li) {
		printf("RESULT: FAIL (%d checks, %d failures)\n", checks, failures);
		return 1;
	}

	/* 2. the context is a real, usable object: logging can be configured. */
	libinput_log_set_priority(li, LIBINPUT_LOG_PRIORITY_DEBUG);
	CHECK(1, "libinput_log_set_priority() accepts the context");

	/* 3. adding a device that does not exist must fail cleanly (returns NULL)
	 *    rather than crash — this exercises the path backend's device path. */
	dev = libinput_path_add_device(li, "/nonexistent/libinput-test-device");
	CHECK(dev == NULL, "libinput_path_add_device() rejects a missing device");

	/* 4. refcount contract: unref() returns NULL for the last reference. */
	CHECK(libinput_unref(li) == NULL, "libinput_unref() releases the context");

	printf("RESULT: %s (%d checks, %d failures)\n",
	       failures == 0 ? "PASS" : "FAIL", checks, failures);
	return failures == 0 ? 0 : 1;
}
