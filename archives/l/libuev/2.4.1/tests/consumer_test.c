/*
 * libuev consumer test — simulates an upstream business component/application
 * that uses libuev only through its installed public header (uev/uev.h),
 * public API, normal link target and runtime artifacts, exactly as a
 * third-party consumer would after `conan install libuev/2.4.1`.
 *
 * Covered public APIs:
 *   uev_init / uev_timer_init / uev_run / uev_exit
 * Observable result: a periodic timer fires N times inside the event loop,
 * then the loop exits cleanly with code 0.
 */
#include <stdio.h>

#include <uev/uev.h>

#define FIRES_REQUIRED 3

static int fires = 0;

static void periodic_cb(uev_t *w, void *arg, int events)
{
	uev_ctx_t *ctx = arg;

	fires++;
	printf("[consumer] periodic timer fired %d/%d (events=0x%x)\n",
	       fires, FIRES_REQUIRED, events);
	if (fires >= FIRES_REQUIRED)
		uev_exit(ctx);
}

int main(void)
{
	uev_ctx_t ctx;
	uev_t timer;

	if (uev_init(&ctx)) {
		fprintf(stderr, "[consumer] uev_init failed\n");
		return 1;
	}

	/* Business-style periodic timer: 100ms period */
	if (uev_timer_init(&ctx, &timer, periodic_cb, &ctx, 100, 100)) {
		fprintf(stderr, "[consumer] uev_timer_init failed\n");
		return 1;
	}

	if (uev_run(&ctx, 0)) {
		fprintf(stderr, "[consumer] uev_run failed\n");
		return 1;
	}

	if (fires != FIRES_REQUIRED) {
		fprintf(stderr, "[consumer] FAIL: expected %d firings, got %d\n",
			FIRES_REQUIRED, fires);
		return 1;
	}

	printf("[consumer] libuev periodic event loop consumer test: PASS\n");
	return 0;
}
