/*
 * libliftoff 0.5.0 — L1 consumer test (HarmonyOS PC / aarch64).
 *
 * Two things are verified here:
 *
 *   1. The library links and its public header is usable — a consumer can
 *      include <libliftoff.h> and reference the API.
 *   2. liftoff_device_create() behaves correctly on a file descriptor that is
 *      not a DRM node.  That is the only device-level path reachable on this
 *      machine: HarmonyOS PC ships no /dev/dri (see ../notes.md), so the
 *      DRM-dependent objects (output/layer/plane) cannot be constructed.
 *      Passing a valid-but-non-DRM fd still drives the real code — dup(), then
 *      drmModeGetResources() — and must yield NULL rather than crash or leak.
 *
 * The allocation logic itself is covered by the upstream unit suite, which
 * `conan create` runs during build() against a mock libdrm (test/libdrm_mock.c).
 *
 * Conan builds in Release, where NDEBUG turns assert() into a no-op, so every
 * check is explicit and prints a step tag before exiting non-zero.
 */
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <unistd.h>

#include <libliftoff.h>

#define CHECK(cond, step, msg)                                                \
	do {                                                                    \
		if (!(cond)) {                                                  \
			fprintf(stderr, "FAIL [%s] %s\n", (step), (msg));        \
			return 1;                                                \
		}                                                               \
		printf("ok   [%s]\n", (step));                                   \
	} while (0)

int main(void) {
	/* libliftoff has no version function; referencing the API symbols from
	 * the public header is what proves the link and the header agree. */
	struct liftoff_device *(*create_fn)(int) = liftoff_device_create;
	void (*destroy_fn)(struct liftoff_device *) = liftoff_device_destroy;
	CHECK(create_fn != NULL && destroy_fn != NULL, "api symbols",
	      "libliftoff symbols are not resolvable");

	/* ── invalid fd: negative descriptor must be rejected ───────────── */
	CHECK(liftoff_device_create(-1) == NULL, "create(-1)",
	      "a negative fd was accepted as a DRM node");

	/* ── valid fd that is not DRM (/dev/null) ──────────────────────── */
	int fd = open("/dev/null", O_RDWR);
	CHECK(fd >= 0, "open(/dev/null)", "could not open /dev/null");
	CHECK(liftoff_device_create(fd) == NULL, "create(non-drm fd)",
	      "a non-DRM fd was accepted as a DRM node");
	/* liftoff_device_create() duplicates the fd it is given
	 * (device.c: `device->drm_fd = dup(drm_fd)`), so on failure it must not
	 * have consumed ours. */
	CHECK(fcntl(fd, F_GETFD) >= 0, "caller fd still open",
	      "the library closed a caller-owned descriptor on failure");
	close(fd);

	/* ── a /dev/dri node, if this platform has one ──────────────────── */
	int drm_fd = open("/dev/dri/card0", O_RDWR);
	int drm_errno = errno;
	if (drm_fd >= 0) {
		struct liftoff_device *device = liftoff_device_create(drm_fd);
		CHECK(device != NULL, "create(/dev/dri/card0)",
		      "a real DRM node was rejected");
		CHECK(liftoff_device_register_all_planes(device) == 0,
		      "register_all_planes", "plane registration failed");
		liftoff_device_destroy(device);
	} else {
		/* Expected on HarmonyOS PC: no DRM device node exists.  Record it
		 * rather than silently skipping, so the log states what ran. */
		printf("skip [/dev/dri/card0] no DRM device node on this platform "
		       "(errno=%d)\n", drm_errno);
	}

	printf("OK: libliftoff links, and rejects non-DRM file descriptors\n");
	return 0;
}
