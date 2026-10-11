/*
 * mock_daemon.c — userspace AF_UNIX datagram peer for the ydotool consumer test.
 *
 * Implements the ydotoold-side wire protocol so the packaged `ydotool` client
 * can be exercised without /dev/uinput (which HarmonyOS PC does not expose to
 * ordinary user processes): the client blindly write(2)s one `struct
 * input_event` per datagram to the daemon socket, so receiving datagrams and
 * decoding them is sufficient to verify the exact event stream.
 *
 * Usage: mock_daemon <socket-path> <expected-event-count>
 *
 * Protocol/output contract (consumed by test.sh):
 *   - "LISTENING" is printed after bind(2), before the first recv(2);
 *   - each received datagram prints "EV <idx> type=<t> code=<c> value=<v>";
 *   - "DONE" + exit 0 once <expected-event-count> datagrams were received;
 *   - "TIMEOUT" + exit 1 if fewer arrive within 10 s;
 *   - "BADSIZE <n>" + exit 1 if a datagram is not exactly one input_event.
 *
 * Exit codes: 0 complete, 1 protocol/timeout failure, 2 setup failure.
 */
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <sys/un.h>
#include <unistd.h>

#include <linux/input.h>

int main(int argc, char **argv)
{
	if (argc != 3) {
		fprintf(stderr, "usage: %s <socket-path> <expected-count>\n", argv[0]);
		return 2;
	}

	const char *path = argv[1];
	int expected = atoi(argv[2]);
	if (expected < 0) {
		fprintf(stderr, "invalid expected count: %s\n", argv[2]);
		return 2;
	}

	unlink(path);

	int fd = socket(AF_UNIX, SOCK_DGRAM, 0);
	if (fd < 0) {
		perror("socket");
		return 2;
	}

	struct sockaddr_un sa;
	memset(&sa, 0, sizeof(sa));
	sa.sun_family = AF_UNIX;
	snprintf(sa.sun_path, sizeof(sa.sun_path), "%s", path);

	if (bind(fd, (const struct sockaddr *)&sa, sizeof(sa)) != 0) {
		/* E024: HarmonyOS SELinux denies AF_UNIX bind() with EPERM on every
		 * writable filesystem, so test.sh treats a clean EPERM as a platform
		 * capability probe rather than a product failure. */
		printf("BIND-FAILED errno=%d %s\n", errno, strerror(errno));
		fflush(stdout);
		close(fd);
		return 2;
	}

	struct timeval tv;
	tv.tv_sec = 10;
	tv.tv_usec = 0;
	setsockopt(fd, SOL_SOCKET, SO_RCVTIMEO, &tv, sizeof(tv));

	/* Readiness marker for test.sh (printed after a successful bind). */
	printf("LISTENING\n");
	fflush(stdout);

	int got = 0;
	while (got < expected) {
		struct input_event ev;
		ssize_t n = recv(fd, &ev, sizeof(ev), 0);
		if (n < 0) {
			if (errno == EAGAIN || errno == EWOULDBLOCK) {
				printf("TIMEOUT after %d/%d events\n", got, expected);
				fflush(stdout);
				unlink(path);
				close(fd);
				return 1;
			}
			perror("recv");
			unlink(path);
			close(fd);
			return 2;
		}
		if ((size_t)n != sizeof(ev)) {
			printf("BADSIZE %ld (expected %zu)\n", (long)n, sizeof(ev));
			fflush(stdout);
			unlink(path);
			close(fd);
			return 1;
		}
		printf("EV %d type=%u code=%u value=%d\n", got, ev.type, ev.code, ev.value);
		fflush(stdout);
		got++;
	}

	printf("DONE\n");
	fflush(stdout);
	unlink(path);
	close(fd);
	return 0;
}
