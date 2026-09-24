/* librtpi 1.0.0 consumer usability checks (Conan test_package, HarmonyOS).
 *
 * Error-path and option coverage that is fully kernel-independent, so the
 * consumer contract holds regardless of the target kernel's PI futex
 * support (HarmonyOS PC kernels currently lack FUTEX_*_REQUEUE_PI):
 *   A - RTPI_MUTEX_PSHARED mutex init + fast-path lock/unlock
 *   B - pi_mutex_init rejects unknown flags with EINVAL
 *   C - pi_cond_init rejects unknown flags with EINVAL
 *   D - self-deadlock detection: pi_mutex_lock returns EDEADLK
 *   E - unlocking a mutex owned by another thread returns EPERM
 *   F - pi_cond_timedwait validates the timespec before blocking (EINVAL)
 */
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>

#include "rtpi.h"

static int failures;
static pi_mutex_t *g_mutex;
static volatile int g_eperm_seen;

#define CHECK(expr)                                                     \
	do {                                                            \
		if (!(expr)) {                                          \
			fprintf(stderr, "FAIL: %s at %s:%d\n",          \
				#expr, __FILE__, __LINE__);             \
			failures++;                                     \
		}                                                       \
	} while (0)

static void *wrong_owner_thread(void *arg)
{
	(void)arg;

	/* The main thread owns g_mutex; unlocking here must fail with
	 * EPERM before any syscall (ownership check is a tid compare). */
	if (pi_mutex_unlock(g_mutex) == EPERM)
		g_eperm_seen = 1;
	return NULL;
}

int main(void)
{
	pthread_t th;
	pi_cond_t *cond;
	struct timespec bad_ts;

	g_mutex = pi_mutex_alloc();
	CHECK(g_mutex != NULL);

	/* A: PSHARED mutex accepted, fast path works. */
	CHECK(pi_mutex_init(g_mutex, RTPI_MUTEX_PSHARED) == 0);
	CHECK(pi_mutex_trylock(g_mutex) == 0);
	CHECK(pi_mutex_unlock(g_mutex) == 0);

	/* B: unknown mutex flags rejected. */
	CHECK(pi_mutex_init(g_mutex, 0x2) == EINVAL);

	/* C: unknown cond flags rejected. */
	cond = pi_cond_alloc();
	CHECK(cond != NULL);
	CHECK(pi_cond_init(cond, 0x8) == EINVAL);

	/* D: self-deadlock detection. */
	CHECK(pi_mutex_init(g_mutex, 0) == 0);
	CHECK(pi_mutex_lock(g_mutex) == 0);
	CHECK(pi_mutex_lock(g_mutex) == EDEADLK);

	/* E: cross-thread unlock rejected. */
	CHECK(pthread_create(&th, NULL, wrong_owner_thread, NULL) == 0);
	CHECK(pthread_join(th, NULL) == 0);
	CHECK(g_eperm_seen == 1);
	CHECK(pi_mutex_unlock(g_mutex) == 0);

	/* F: timespec validation happens before blocking. */
	CHECK(pi_mutex_lock(g_mutex) == 0);
	bad_ts.tv_sec = 1;
	bad_ts.tv_nsec = -1;
	CHECK(pi_cond_timedwait(cond, g_mutex, &bad_ts) == EINVAL);
	CHECK(pi_mutex_unlock(g_mutex) == 0);

	CHECK(pi_cond_destroy(cond) == 0);
	pi_cond_free(cond);
	CHECK(pi_mutex_destroy(g_mutex) == 0);
	pi_mutex_free(g_mutex);

	if (failures) {
		fprintf(stderr, "consumer_checks: %d failure(s)\n", failures);
		return 1;
	}
	printf("librtpi consumer checks passed (error paths + PSHARED)\n");
	return 0;
}
