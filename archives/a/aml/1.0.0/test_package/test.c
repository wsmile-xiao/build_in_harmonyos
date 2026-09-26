#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <aml.h>

/* Consumer-style test for the aml (Another Main Loop) library.
 *
 * Uses only the public installed API from <aml1/aml.h>:
 *   - aml_new / aml_set_default / aml_get_default
 *   - aml_ticker_new / aml_start / aml_unref
 *   - aml_run / aml_exit
 *   - aml_get_userdata / aml_version (global string)
 *
 * Verifies that the event loop runs, a ticker callback fires with an
 * observable result, and the loop terminates cleanly.
 */

static int tick_count = 0;

static void on_tick(struct aml_ticker* ticker)
{
	(void)ticker;
	tick_count++;
}

static void on_timeout_exit(struct aml_timer* timer)
{
	(void)timer;
	aml_exit(aml_get_default());
}

static void on_sigint(struct aml_signal* sig)
{
	(void)sig;
	aml_exit(aml_get_default());
}

int main(void)
{
	const char* version = aml_version;
	if (!version || !*version) {
		fprintf(stderr, "FAIL: aml_version string is empty\n");
		return 1;
	}
	printf("aml version: %s\n", version);

	struct aml* loop = aml_new();
	if (!loop) {
		fprintf(stderr, "FAIL: aml_new() returned NULL\n");
		return 1;
	}
	aml_set_default(loop);

	/* Ticker fires every 50 ms; let it run for a few ticks. */
	struct aml_ticker* ticker = aml_ticker_new(50000, on_tick, NULL, NULL);
	if (!ticker) {
		fprintf(stderr, "FAIL: aml_ticker_new() returned NULL\n");
		aml_unref(loop);
		return 1;
	}
	if (aml_start(loop, ticker) < 0) {
		fprintf(stderr, "FAIL: aml_start(ticker) failed\n");
		aml_unref(ticker);
		aml_unref(loop);
		return 1;
	}

	/* Hard stop after 500 ms so the test cannot hang. */
	struct aml_timer* timer = aml_timer_new(500000, on_timeout_exit, NULL, NULL);
	if (timer)
		aml_start(loop, timer);

	int rc = aml_run(loop);

	aml_unref(ticker);
	if (timer)
		aml_unref(timer);
	aml_unref(loop);

	if (rc != 0) {
		fprintf(stderr, "FAIL: aml_run() returned %d\n", rc);
		return 1;
	}
	if (tick_count <= 0) {
		fprintf(stderr, "FAIL: ticker callback never fired (tick_count=%d)\n",
			tick_count);
		return 1;
	}

	printf("PASS: aml event loop ran, ticker fired %d time(s)\n", tick_count);
	return 0;
}
