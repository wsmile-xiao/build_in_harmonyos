/* libpri 1.6.0 consumer / adaptation test (HarmonyOS PC aarch64).
 *
 * Links the *installed* libpri (include/libpri.h + lib/libpri.a) and:
 *   1. asserts the packaged version fingerprint,
 *   2. exercises the public string/table helpers,
 *   3. exercises the pri_sr_* SETUP-request lifecycle,
 *   4. drives a real Q.921/Q.931 exchange between two libpri stacks
 *      (PRI_NETWORK + PRI_CPE) joined by a socketpair(): the NETWORK side
 *      places a call, the CPE side must receive it as PRI_EVENT_RING with the
 *      dialled number, and the NETWORK side must receive the CPE's ALERTING
 *      as PRI_EVENT_RINGING.  That proves frames are encoded, transmitted and
 *      decoded across both ends by the installed library.
 *
 * Every CHECK() below executes exactly once, so the runtime count printed at
 * the end equals the number of CHECK sites (no loop-driven repeats).
 *
 * Exits non-zero if any check fails.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/select.h>
#include <sys/socket.h>

#include "libpri.h"

#define SWITCHTYPE PRI_SWITCH_NI2
#define DIALED "1000"

static int g_checks;
static int g_failed;

#define CHECK(cond, msg)                            \
	do {                                        \
		g_checks++;                         \
		if (cond) {                         \
			printf("ok   - %s\n", (msg)); \
		} else {                            \
			g_failed++;                 \
			printf("FAIL - %s\n", (msg)); \
		}                                   \
	} while (0)

struct endpoint {
	struct pri *pri;
	const char *tag;
	int dchan_up;
	int ring;
	int ringing;
	int unknown;
	int placed;
	int call_rc;
	char called[64];
};

static void on_event(struct endpoint *ep, pri_event *ev)
{
	if (!ev) {
		return;
	}
	switch (ev->gen.e) {
	case PRI_EVENT_DCHAN_UP:
		ep->dchan_up = 1;
		printf("     [%s] D-Channel up\n", ep->tag);
		/* Only the network side places the call; the CPE side answers. */
		if (ep->tag[0] == 'N' && !ep->placed) {
			ep->placed = 1;
			ep->call_rc = pri_call(
				ep->pri, pri_new_call(ep->pri), PRI_TRANS_CAP_SPEECH,
				1, 1, 1, "2001", PRI_NATIONAL_ISDN, "Caller",
				PRES_ALLOWED_USER_NUMBER_PASSED_SCREEN, DIALED,
				PRI_NATIONAL_ISDN, PRI_LAYER_1_ULAW);
			printf("     [%s] pri_call() rc=%d\n", ep->tag, ep->call_rc);
		}
		break;
	case PRI_EVENT_DCHAN_DOWN:
		ep->dchan_up = 0;
		break;
	case PRI_EVENT_RING:
		ep->ring++;
		if (ev->ring.callednum[0]) {
			snprintf(ep->called, sizeof(ep->called), "%s",
				 ev->ring.callednum);
		}
		printf("     [%s] RING called=%s channel=%d\n", ep->tag,
		       ep->called, ev->ring.channel);
		if (ev->ring.call) {
			pri_proceeding(ep->pri, ev->ring.call, ev->ring.channel, 0);
			pri_acknowledge(ep->pri, ev->ring.call, ev->ring.channel, 0);
		}
		break;
	case PRI_EVENT_RINGING:
		ep->ringing++;
		printf("     [%s] RINGING\n", ep->tag);
		break;
	/* Events this scenario may legitimately deliver; counted as expected. */
	case PRI_EVENT_PROCEEDING:
	case PRI_EVENT_SETUP_ACK:
	case PRI_EVENT_INFO_RECEIVED:
	case PRI_EVENT_HANGUP:
	case PRI_EVENT_HANGUP_ACK:
	case PRI_EVENT_RESTART:
	case PRI_EVENT_RESTART_ACK:
	case PRI_EVENT_FACILITY:
	case PRI_EVENT_NOTIFY:
	case PRI_EVENT_PROGRESS:
	case PRI_EVENT_KEYPAD_DIGIT:
	case PRI_EVENT_SERVICE:
	case PRI_EVENT_SERVICE_ACK:
	case PRI_EVENT_HOLD:
	case PRI_EVENT_HOLD_ACK:
	case PRI_EVENT_HOLD_REJ:
	case PRI_EVENT_RETRIEVE:
	case PRI_EVENT_RETRIEVE_ACK:
	case PRI_EVENT_RETRIEVE_REJ:
	case PRI_EVENT_CONNECT_ACK:
		break;
	default:
		ep->unknown++;
		break;
	}
}

int main(void)
{
	int sv[2];
	struct endpoint net = {0}, cpe = {0};
	struct pri_sr *sr = NULL;
	char *dump = NULL;
	const char *version;
	char *ring_str;
	char *answer_str;
	char *cause_str;
	int iter;

	net.tag = "NET";
	cpe.tag = "CPE";

	/* ---- 1. packaged version fingerprint ---- */
	version = pri_get_version();
	printf("     pri_get_version() = %s\n", version ? version : "<null>");
	CHECK(version != NULL && version[0] != '\0',
	      "pri_get_version() returns non-empty text");
	CHECK(version != NULL && strcmp(version, "1.6.0") == 0,
	      "pri_get_version() reports the packaged release 1.6.0");

	/* ---- 2. public string / table helpers ---- */
	ring_str = pri_event2str(PRI_EVENT_RING);
	answer_str = pri_event2str(PRI_EVENT_ANSWER);
	cause_str = pri_cause2str(PRI_CAUSE_NORMAL_CLEARING);
	CHECK(ring_str != NULL && ring_str[0] != '\0',
	      "pri_event2str(PRI_EVENT_RING) returns non-empty text");
	CHECK(answer_str != NULL && ring_str != NULL &&
	      strcmp(ring_str, answer_str) != 0,
	      "pri_event2str() distinguishes PRI_EVENT_RING from PRI_EVENT_ANSWER");
	CHECK(cause_str != NULL && cause_str[0] != '\0',
	      "pri_cause2str(PRI_CAUSE_NORMAL_CLEARING) returns non-empty text");
	CHECK(cause_str != NULL && strstr(cause_str, "Normal") != NULL,
	      "pri_cause2str() resolves the normal-clearing cause name");
	CHECK(pri_switch2str(PRI_SWITCH_NI2) != NULL &&
	      pri_switch2str(PRI_SWITCH_NI2)[0] != '\0',
	      "pri_switch2str(PRI_SWITCH_NI2) returns non-empty text");
	CHECK(pri_node2str(PRI_NETWORK) != NULL &&
	      pri_node2str(PRI_NETWORK)[0] != '\0',
	      "pri_node2str(PRI_NETWORK) returns non-empty text");

	/* ---- 3. pri_sr_* SETUP-request lifecycle ---- */
	sr = pri_sr_new();
	CHECK(sr != NULL, "pri_sr_new() returns a SETUP-request handle");
	if (sr != NULL) {
		CHECK(pri_sr_set_channel(sr, 1, 1, 0) == 0,
		      "pri_sr_set_channel() accepts a B-channel");
		CHECK(pri_sr_set_bearer(sr, PRI_TRANS_CAP_SPEECH,
					PRI_LAYER_1_ULAW) == 0,
		      "pri_sr_set_bearer() accepts speech/ulaw");
		CHECK(pri_sr_set_called(sr, DIALED, PRI_NATIONAL_ISDN, 1) == 0,
		      "pri_sr_set_called() accepts the dialled number");
		CHECK(pri_sr_set_caller(sr, "2001", "Caller",
					PRI_NATIONAL_ISDN,
					PRES_ALLOWED_USER_NUMBER_PASSED_SCREEN) == 0,
		      "pri_sr_set_caller() accepts the caller identity");
		pri_sr_free(sr);
	}

	/* ---- 4. two libpri stacks over a socketpair ---- */
	CHECK(socketpair(AF_LOCAL, SOCK_DGRAM, 0, sv) == 0,
	      "socketpair(AF_LOCAL, SOCK_DGRAM) succeeds");
	net.pri = pri_new_bri(sv[0], 0, PRI_NETWORK, SWITCHTYPE);
	cpe.pri = pri_new_bri(sv[1], 0, PRI_CPE, SWITCHTYPE);
	CHECK(net.pri != NULL, "pri_new_bri(PRI_NETWORK) returns a controller");
	CHECK(cpe.pri != NULL, "pri_new_bri(PRI_CPE) returns a controller");
	CHECK(net.pri != NULL && pri_fd(net.pri) == sv[0],
	      "pri_fd() exposes the network-side D-channel descriptor");
	CHECK(cpe.pri != NULL && pri_fd(cpe.pri) == sv[1],
	      "pri_fd() exposes the CPE-side D-channel descriptor");
	CHECK(net.pri != NULL && pri_new_call(net.pri) != NULL,
	      "pri_new_call() returns a call record");

	dump = net.pri ? pri_dump_info_str(net.pri) : NULL;
	CHECK(dump != NULL && dump[0] != '\0',
	      "pri_dump_info_str() renders the controller state");
	free(dump);

	/* Pump both ends until the CPE has seen the SETUP and the network has
	 * seen the CPE's ALERTING (typically ~12 iterations; hard-capped). */
	if (net.pri != NULL && cpe.pri != NULL) {
		for (iter = 0; iter < 20000; iter++) {
			fd_set fds;
			struct timeval tv;
			int maxfd = -1;
			int res;

			if (cpe.ring >= 1 && net.ringing >= 1) {
				break;
			}
			FD_ZERO(&fds);
			FD_SET(pri_fd(net.pri), &fds);
			FD_SET(pri_fd(cpe.pri), &fds);
			maxfd = pri_fd(net.pri) > pri_fd(cpe.pri)
					? pri_fd(net.pri)
					: pri_fd(cpe.pri);
			tv.tv_sec = 0;
			tv.tv_usec = 1000;
			res = select(maxfd + 1, &fds, NULL, NULL, &tv);
			if (res > 0) {
				if (FD_ISSET(pri_fd(net.pri), &fds)) {
					on_event(&net, pri_check_event(net.pri));
				}
				if (FD_ISSET(pri_fd(cpe.pri), &fds)) {
					on_event(&cpe, pri_check_event(cpe.pri));
				}
			} else if (res == 0) {
				/* Drive retransmit / T200-T203 timers. */
				on_event(&net, pri_schedule_run(net.pri));
				on_event(&cpe, pri_schedule_run(cpe.pri));
			}
		}
		printf("     loopback converged after %d pump iterations\n", iter);

		CHECK(net.dchan_up == 1,
		      "network side reached PRI_EVENT_DCHAN_UP");
		CHECK(cpe.dchan_up == 1,
		      "CPE side reached PRI_EVENT_DCHAN_UP");
		CHECK(net.call_rc == 0,
		      "pri_call() accepted the outgoing SETUP");
		CHECK(cpe.ring == 1,
		      "CPE received exactly one PRI_EVENT_RING");
		CHECK(strcmp(cpe.called, DIALED) == 0,
		      "the received SETUP carried the dialled number 1000");
		CHECK(net.ringing >= 1,
		      "network side decoded the CPE's ALERTING as PRI_EVENT_RINGING");
		CHECK(net.unknown == 0 && cpe.unknown == 0,
		      "no unexpected PRI event reached either endpoint");
	} else {
		CHECK(0, "both PRI controllers were created for the loopback");
	}

	printf("\n%d checks, %d failed\n", g_checks, g_failed);
	return g_failed == 0 ? 0 : 1;
}
