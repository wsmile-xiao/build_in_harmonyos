/*
 * test_package consumer test for libtelnet 0.23
 *
 * Real API exercise: creates a telnet state tracker, feeds it data
 * (including a negotiation command), and asserts events arrive via the
 * event handler. Exits non-zero on any failure (R34: substantive test).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <libtelnet.h>

static int event_count = 0;
static int data_received = 0;

static void handler(telnet_t *telnet, telnet_event_t *event,
		void *user_data) {
	(void)telnet;
	(void)user_data;
	switch (event->type) {
	case TELNET_EV_DATA:
		if (event->data.buffer && event->data.size > 0)
			data_received = 1;
		event_count++;
		break;
	case TELNET_EV_DO:
	case TELNET_EV_WILL:
	case TELNET_EV_SEND:
		event_count++;
		break;
	default:
		event_count++;
		break;
	}
}

int main(void) {
	/* Create telnet state tracker. */
	telnet_t *telnet = telnet_init(NULL, handler, 0, NULL);
	if (telnet == NULL) {
		fprintf(stderr, "FAIL: telnet_init() returned NULL\n");
		return 1;
	}

	/* Feed plain data through the state tracker. */
	telnet_recv(telnet, "hello", 5);

	/* Feed an IAC DO negotiation command (IAC DO SGA). */
	{
		static const unsigned char cmd[3] = {
			(unsigned char)255, (unsigned char)253, (unsigned char)3
		};
		telnet_recv(telnet, (const char *)cmd, 3);
	}

	/* Send data through the tracker (escapes IAC bytes). */
	telnet_send(telnet, "world", 5);

	telnet_free(telnet);

	if (event_count == 0) {
		fprintf(stderr, "FAIL: no events received from telnet state tracker\n");
		return 1;
	}
	if (!data_received) {
		fprintf(stderr, "FAIL: no data event delivered\n");
		return 1;
	}

	printf("PASS: libtelnet 0.23 consumer test OK (events=%d data=1)\n",
		event_count);
	return 0;
}
