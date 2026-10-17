/* Consumer-side test of the public libseat API through its noop backend. */
#define _POSIX_C_SOURCE 200809L

#include <errno.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include "libseat.h"

static int checks;
static int failures;
static int enable_calls;
static int log_calls;

#define CHECK(condition, message)                                             \
	do {                                                                   \
		checks++;                                                      \
		if (condition) {                                               \
			printf("ok %02d - %s\n", checks, message);              \
		} else {                                                       \
			failures++;                                            \
			printf("not ok %02d - %s (errno=%d: %s)\n", checks,  \
			       message, errno, strerror(errno));                \
		}                                                              \
	} while (0)

static void enable_seat(struct libseat *seat, void *userdata)
{
	(void)seat;
	(void)userdata;
	enable_calls++;
}

static void disable_seat(struct libseat *seat, void *userdata)
{
	(void)userdata;
	libseat_disable_seat(seat);
}

static void count_log(enum libseat_log_level level, const char *format,
		      va_list arguments)
{
	(void)level;
	(void)format;
	(void)arguments;
	log_calls++;
}

static const struct libseat_seat_listener listener = {
	.enable_seat = enable_seat,
	.disable_seat = disable_seat,
};

static const char *make_device_file(void)
{
	static const char *path = "libseat_test_device.tmp";
	FILE *file = fopen(path, "w");

	if (file == NULL)
		return NULL;
	fputs("libseat test device\n", file);
	fclose(file);
	return path;
}

int main(void)
{
	struct libseat *seat;
	const char *name;
	const char *device_path;
	int fd = -1;
	int device_id;
	int result;

	libseat_set_log_handler(count_log);
	libseat_set_log_level(LIBSEAT_LOG_LEVEL_ERROR);

	errno = 0;
	seat = libseat_open_seat(NULL, NULL);
	CHECK(seat == NULL && errno == EINVAL,
	      "NULL listener is rejected with EINVAL");

	const struct libseat_seat_listener incomplete_listener = {
		.enable_seat = NULL,
		.disable_seat = disable_seat,
	};
	errno = 0;
	seat = libseat_open_seat(&incomplete_listener, NULL);
	CHECK(seat == NULL && errno == EINVAL,
	      "listener without enable callback is rejected");

	log_calls = 0;
	setenv("LIBSEAT_BACKEND", "seatd-conan-missing-backend", 1);
	errno = 0;
	seat = libseat_open_seat(&listener, NULL);
	CHECK(seat == NULL && errno == EINVAL,
	      "unknown backend is rejected with EINVAL");
	CHECK(log_calls > 0, "backend error reaches the configured log handler");

	setenv("LIBSEAT_BACKEND", "noop", 1);
	enable_calls = 0;
	errno = 0;
	seat = libseat_open_seat(&listener, NULL);
	CHECK(seat != NULL, "noop backend opens a seat");
	if (seat == NULL)
		return 1;

	name = libseat_seat_name(seat);
	CHECK(name != NULL && strcmp(name, "seat0") == 0,
	      "seat name is seat0");

	fd = libseat_get_fd(seat);
	CHECK(fd >= 0, "seat exposes a pollable descriptor");

	result = libseat_dispatch(seat, 0);
	CHECK(result >= 0, "non-blocking dispatch succeeds");
	CHECK(enable_calls == 1, "first dispatch invokes enable callback once");

	enable_calls = 0;
	setenv("LIBSEAT_BACKEND", "noop", 1);
	result = libseat_switch_session(seat, 2);
	CHECK(result < 0,
	      "noop backend reports session switch failure");
	CHECK(enable_calls == 0,
	      "failed session switch does not re-enable the seat");

	device_path = make_device_file();
	CHECK(device_path != NULL, "test device file is created");
	if (device_path == NULL)
		return 1;

	device_id = libseat_open_device(seat, device_path, &fd);
	CHECK(device_id >= 0, "device open succeeds");
	if (device_id >= 0) {
		CHECK(fd >= 0, "device open returns a file descriptor");
		result = libseat_close_device(seat, device_id);
		CHECK(result == 0, "device close succeeds");
	}

	unlink(device_path);
	result = libseat_close_seat(seat);
	CHECK(result == 0, "seat close succeeds");

	if (failures == 0)
		printf("PASS: libseat consumer test (%d checks)\n", checks);
	else
		printf("FAIL: libseat consumer test (%d/%d checks passed)\n",
		       checks - failures, checks);

	return failures == 0 ? 0 : 1;
}