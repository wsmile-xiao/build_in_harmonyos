/*
 * Consumer-side smoke test for libratbag 0.18 (liblur).
 *
 * Everything asserted here is hardware-free: it exercises the parts of the
 * public liblur API that are pure computation or that must fail gracefully on
 * a machine without a Logitech Unifying Receiver.  That matters on OHOS PC:
 * the CI target has no /dev/hidraw node, so any test that needed a receiver
 * plugged in would be unrunnable.
 *
 * What is checked:
 *   * the ABI of enum lur_device_type, as seen through the *installed*
 *     <liblur.h>, against the values the upstream header pins;
 *   * lur_is_receiver() classification for the two upstream receiver PIDs,
 *     for a real-but-non-receiver Logitech PID, and for a foreign vendor;
 *   * lur_receiver_new_from_hidraw() error contract: a bad fd yields the
 *     documented -EINVAL and leaves the out-parameter untouched (this is the
 *     documented contract, and it is the only code path reachable without
 *     hardware);
 *   * lur_receiver_new_from_hidraw() rejects a *valid but non-hidraw*
 *     descriptor the same way, i.e. the HIDIOCGRAWINFO probe is really
 *     consulted rather than the fd being taken at face value.
 */

#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <liblur.h>

static int checks = 0;

#define CHECK(cond)                                                            \
	do {                                                                   \
		checks++;                                                      \
		if (!(cond)) {                                                 \
			fprintf(stderr, "FAIL %s:%d: %s\n", __FILE__, __LINE__, \
				#cond);                                        \
			exit(1);                                               \
		}                                                              \
	} while (0)

/* Logitech's vendor id, and the two PIDs liblur recognises as receivers. */
#define LOGITECH 0x046d
#define PID_LUR_RECEIVER 0xc52b
#define PID_LUR_RECEIVER_NANO 0xc532
/* A genuine Logitech product id that is *not* a unifying receiver. */
#define PID_NOT_A_RECEIVER 0xc534
/* A vendor id that is not Logitech at all. */
#define VID_FOREIGN 0x1234

static void
check_device_type_abi(void)
{
	/* These numeric values are the on-the-wire meanings reported by the
	 * HID++ device-type feature; a consumer switch-casing on them must get
	 * the same numbers out of the installed header. */
	CHECK(LUR_DEVICE_TYPE_UNKNOWN == 0x00);
	CHECK(LUR_DEVICE_TYPE_KEYBOARD == 0x01);
	CHECK(LUR_DEVICE_TYPE_MOUSE == 0x02);
	CHECK(LUR_DEVICE_TYPE_NUMPAD == 0x03);
	CHECK(LUR_DEVICE_TYPE_PRESENTER == 0x04);
	CHECK(LUR_DEVICE_TYPE_TRACKBALL == 0x08);
	CHECK(LUR_DEVICE_TYPE_TOUCHPAD == 0x09);

	/* Every declared type is a distinct value. */
	CHECK(LUR_DEVICE_TYPE_KEYBOARD != LUR_DEVICE_TYPE_MOUSE);
	CHECK(LUR_DEVICE_TYPE_TRACKBALL != LUR_DEVICE_TYPE_TOUCHPAD);
}

static void
check_is_receiver(void)
{
	/* Both unifying receiver models are recognised. */
	CHECK(lur_is_receiver(LOGITECH, PID_LUR_RECEIVER) != 0);
	CHECK(lur_is_receiver(LOGITECH, PID_LUR_RECEIVER_NANO) != 0);

	/* A Logitech pid that is not a receiver, and a receiver pid from a
	 * foreign vendor, are both rejected. */
	CHECK(lur_is_receiver(LOGITECH, PID_NOT_A_RECEIVER) == 0);
	CHECK(lur_is_receiver(VID_FOREIGN, PID_LUR_RECEIVER) == 0);
	CHECK(lur_is_receiver(VID_FOREIGN, PID_NOT_A_RECEIVER) == 0);

	/* An unplugged/unknown device (0/0) is not a receiver. */
	CHECK(lur_is_receiver(0x0000, 0x0000) == 0);
}

static void
check_bad_fd_rejected(void)
{
	struct lur_receiver *receiver = (struct lur_receiver *)0xdeadbeef;

	/* A negative descriptor can never be a hidraw node.  The documented
	 * error is -EINVAL, and the out-parameter must stay untouched so a
	 * caller that reuses the variable does not end up with a dangling
	 * handle. */
	errno = 0;
	CHECK(lur_receiver_new_from_hidraw(-1, NULL, &receiver) == -EINVAL);
	CHECK(receiver == (struct lur_receiver *)0xdeadbeef);

	/* Same again with a non-NULL userdata, to be sure the failure path
	 * does not depend on it. */
	receiver = (struct lur_receiver *)0xdeadbeef;
	CHECK(lur_receiver_new_from_hidraw(-1, &checks, &receiver) == -EINVAL);
	CHECK(receiver == (struct lur_receiver *)0xdeadbeef);
}

static void
check_non_hidraw_fd_rejected(void)
{
	struct lur_receiver *receiver = (struct lur_receiver *)0xdeadbeef;
	int fd;

	/* /dev/null is a perfectly valid O_RDWR descriptor, but it is not a
	 * hidraw device: HIDIOCGRAWINFO fails, so liblur must refuse it rather
	 * than hand back a receiver object it cannot talk to. */
	fd = open("/dev/null", O_RDWR);
	if (fd < 0) {
		fprintf(stderr, "SKIP: cannot open /dev/null (%s)\n",
			strerror(errno));
		return;
	}

	CHECK(lur_receiver_new_from_hidraw(fd, NULL, &receiver) == -EINVAL);
	CHECK(receiver == (struct lur_receiver *)0xdeadbeef);

	close(fd);
}

int
main(void)
{
	check_device_type_abi();
	check_is_receiver();
	check_bad_fd_rejected();
	check_non_hidraw_fd_rejected();

	printf("test_lur: %d checks passed\n", checks);
	return 0;
}
