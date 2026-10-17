/*
 * libservicelog consumer probe (test_package).
 *
 * Exercises the installed shared library end to end through the public v1
 * API: open with the SERVICELOG_DB env override, log an OS event carrying a
 * FRU callout, query it back, verify the round trip field by field, print
 * it at verbosity 1, then truncate and close. Runs without /var write
 * access (the DB path comes from the environment, per patch 0001).
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <servicelog.h>

static int fails;

#define CHECK(cond, msg) \
	do { \
		if (!(cond)) { \
			fprintf(stderr, "CHECK FAIL: %s\n", msg); \
			fails++; \
		} \
	} while (0)

int main(void)
{
	servicelog *slog = NULL;
	struct sl_event event;
	struct sl_event *events = NULL;
	struct sl_event *ev;
	struct sl_callout callout;
	struct sl_data_os os_data;
	uint64_t id = 0;
	int rc;

	memset(&event, 0, sizeof(event));
	memset(&callout, 0, sizeof(callout));

	/* SL_TYPE_OS requires the os addl-data block (subsystem/driver/device
	 * are mandatory, same as the upstream test driver). */
	os_data.version = (char *)"probe-6.6.0";
	os_data.subsystem = (char *)"probe-subsystem";
	os_data.driver = (char *)"probe-driver";
	os_data.device = (char *)"probe-scsidev";

	rc = servicelog_open(&slog, SL_FLAG_ADMIN);
	CHECK(rc == 0 && slog != NULL, "servicelog_open (SERVICELOG_DB)");

	callout.priority = 'L';
	callout.type = 16;
	callout.procedure = "FSPSP07";
	callout.location = "U787E.001.0458891-P1";
	callout.fru = "MA_BRDG";
	callout.serial = "YL30F4148001";
	callout.ccin = "261C";

	event.time_event = 0;
	event.type = SL_TYPE_OS;
	event.severity = SL_SEV_INFO;
	event.machine_serial = "probe-serial";
	event.machine_model = "probe-model";
	event.refcode = "probe-refcode";
	event.description = "probe consumer event";
	event.serviceable = 0;
	event.predictive = 0;
	event.disposition = SL_DISP_RECOVERABLE;
	event.call_home_status = SL_CALLHOME_NONE;
	event.closed = 1;
	event.addl_data = &os_data;
	event.callouts = &callout;

	rc = servicelog_event_log(slog, &event, &id);
	CHECK(rc == 0 && id > 0, "servicelog_event_log returns id");

	rc = servicelog_event_query(slog, "", &events);
	CHECK(rc == 0 && events != NULL, "servicelog_event_query");

	for (ev = events; ev != NULL; ev = ev->next) {
		if (ev->id != id)
			continue;
		CHECK(ev->type == SL_TYPE_OS, "type round trip");
		CHECK(ev->severity == SL_SEV_INFO, "severity round trip");
		CHECK(strcmp(ev->description, "probe consumer event") == 0,
		      "description round trip");
		CHECK(ev->callouts != NULL
		      && strcmp(ev->callouts->fru, "MA_BRDG") == 0
		      && strcmp(ev->callouts->ccin, "261C") == 0,
		      "callout round trip");
		CHECK(servicelog_event_print(stdout, ev, 1) > 0,
		      "servicelog_event_print verbosity 1");
		break;
	}
	CHECK(events != NULL, "logged event found in query result");
	servicelog_event_free(events);

	rc = servicelog_truncate(slog, 0);
	CHECK(rc == 0, "servicelog_truncate");

	servicelog_close(slog);

	if (fails) {
		fprintf(stderr, "probe: %d check(s) failed\n", fails);
		return 1;
	}
	printf("probe: all checks passed\n");
	return 0;
}
