/* liboeffis 1.6.0 consumer test — real API exercise.
 *
 * Exercises the public liboeffis API:
 *   oeffis_new / oeffis_ref / oeffis_unref (lifecycle)
 *   oeffis_get_fd / oeffis_get_eis_fd
 *   oeffis_create_session_on_bus (failed-connect error path)
 *   oeffis_get_event / oeffis_dispatch
 *   oeffis_get_error_message
 *
 * OHOS has no real XDG RemoteDesktop portal, so the test uses an invalid
 * busname to trigger the documented error path (DISCONNECTED event +
 * error message set). This is the same approach as the upstream
 * test_failed_connect munit test.
 */
#include <errno.h>
#include <stdio.h>

#include <libei-1.0/liboeffis.h>

#define CHECK(cond, msg)                                                       \
	do {                                                                   \
		if (!(cond)) {                                                 \
			fprintf(stderr, "FAIL: %s (line %d)\n", msg, __LINE__);\
			return 1;                                              \
		}                                                              \
	} while (0)

int main(void)
{
	struct oeffis *oeffis;
	struct oeffis *refd;
	int fd;
	int eis_fd;
	enum oeffis_event_type event;
	const char *errmsg;

	printf("=== liboeffis consumer test ===\n");

	/* 1. Lifecycle: new/ref/unref */
	printf("[1] lifecycle: new/ref/unref\n");
	oeffis = oeffis_new(NULL);
	CHECK(oeffis != NULL, "oeffis_new returned NULL");

	refd = oeffis_ref(oeffis);
	CHECK(refd == oeffis, "oeffis_ref did not return same pointer");

	oeffis_unref(refd);
	/* After one unref, still alive (refcount was 2) */
	fd = oeffis_get_fd(oeffis);
	CHECK(fd >= 0, "oeffis_get_fd returned invalid fd");

	oeffis_unref(oeffis);
	/* After second unref, object is destroyed */

	/* 2. get_eis_fd before connection returns -1/ENODEV */
	printf("[2] get_eis_fd before connection\n");
	oeffis = oeffis_new(NULL);
	CHECK(oeffis != NULL, "oeffis_new returned NULL (round 2)");

	eis_fd = oeffis_get_eis_fd(oeffis);
	CHECK(eis_fd == -1, "get_eis_fd should return -1 before connection");
	CHECK(errno == ENODEV, "errno should be ENODEV");

	oeffis_unref(oeffis);

	/* 3. Failed connect: invalid busname triggers DISCONNECTED event */
	printf("[3] failed connect: invalid busname\n");
	oeffis = oeffis_new(NULL);
	CHECK(oeffis != NULL, "oeffis_new returned NULL (round 3)");

	oeffis_create_session_on_bus(oeffis, "foo.bar.Example", 0);

	/* Drain events until DISCONNECTED arrives. The loop is bounded so a
	 * runtime behaviour change fails fast instead of spinning forever in CI. */
	event = OEFFIS_EVENT_NONE;
	for (int i = 0; i < 1000 && event == OEFFIS_EVENT_NONE; i++) {
		oeffis_dispatch(oeffis);
		event = oeffis_get_event(oeffis);
	}
	CHECK(event == OEFFIS_EVENT_DISCONNECTED,
	      "expected DISCONNECTED event");

	errmsg = oeffis_get_error_message(oeffis);
	CHECK(errmsg != NULL, "error message should be set after disconnect");
	printf("    error_message: %s\n", errmsg);

	oeffis_unref(oeffis);

	printf("=== all assertions passed ===\n");
	return 0;
}
