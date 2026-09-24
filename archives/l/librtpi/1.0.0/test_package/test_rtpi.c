/* librtpi 1.0.0 consumer smoke test (Conan L1 test_package).
 *
 * Exercises the public C API end to end:
 *   Phase 1 - alloc/init/trylock/unlock (uncontended CAS fast path)
 *   Phase 2 - contended lock/unlock across two threads, which forces the
 *             FUTEX_LOCK_PI / FUTEX_UNLOCK_PI slow path
 *   Phase 3 - condvar capability probe: a timed wait with no signaler must
 *             either return ETIMEDOUT (kernel implements the PI requeue
 *             futexes) or ENOSYS (kernel does not); anything else fails.
 *   Phase 4 - condvar wait + signal handshake, which forces the
 *             FUTEX_WAIT_REQUEUE_PI / FUTEX_CMP_REQUEUE_PI requeue path
 *             (only run when phase 3 proved kernel support)
 *   Phase 5 - condvar timeout path (ETIMEDOUT with no signaler, mutex
 *             re-acquired on return; only run when supported)
 *   Phase 6 - destroy/free lifecycle
 *
 * librtpi builds priority inheritance on the Linux PI futex syscalls.  The
 * HarmonyOS PC device measured on 2026-09-19 (HongMeng kernel 1.12.0)
 * implements FUTEX_LOCK_PI/FUTEX_UNLOCK_PI but returns ENOSYS for
 * FUTEX_WAIT_REQUEUE_PI/FUTEX_CMP_REQUEUE_PI.  A missing requeue
 * implementation is therefore reported as a platform capability gap
 * (exit 0 with an explicit "condvar: UNSUPPORTED" marker and reason) while
 * every other unexpected behaviour still fails the test — this keeps the
 * mutex API hard-verified without masking real bugs behind the known gap.
 */
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#include "rtpi.h"

static pi_mutex_t *g_mutex;
static pi_cond_t *g_cond;
static volatile int g_worker_acquired;
static volatile int g_cond_supported = 1;

#define CHECK(expr)                                                       \
	do {                                                              \
		if (!(expr)) {                                            \
			fprintf(stderr,                                   \
				"FAIL: %s at %s:%d (errno=%s)\n",         \
				#expr, __FILE__, __LINE__, strerror(errno)); \
			exit(1);                                          \
		}                                                         \
	} while (0)

static void msleep(long ms)
{
	struct timespec ts;

	ts.tv_sec = ms / 1000;
	ts.tv_nsec = (ms % 1000) * 1000000L;
	nanosleep(&ts, NULL);
}

static void abs_deadline(struct timespec *deadline, long seconds)
{
	CHECK(clock_gettime(CLOCK_MONOTONIC, deadline) == 0);
	deadline->tv_sec += seconds;
}

static void *contender_thread(void *arg)
{
	(void)arg;

	/* Blocks in FUTEX_LOCK_PI until the main thread releases the mutex. */
	CHECK(pi_mutex_lock(g_mutex) == 0);
	g_worker_acquired = 1;
	CHECK(pi_mutex_unlock(g_mutex) == 0);
	return NULL;
}

static void *cond_waiter_thread(void *arg)
{
	struct timespec deadline;
	int ret;

	(void)arg;

	/* Default condvar clock is CLOCK_MONOTONIC (RTPI_COND_CLOCK_REALTIME
	 * not set), so build the absolute deadline from CLOCK_MONOTONIC. */
	abs_deadline(&deadline, 5);

	CHECK(pi_mutex_lock(g_mutex) == 0);
	/* Releases the mutex and parks in FUTEX_WAIT_REQUEUE_PI; on wakeup
	 * the thread owns the PI mutex again. */
	ret = pi_cond_timedwait(g_cond, g_mutex, &deadline);
	if (ret != 0) {
		pi_mutex_unlock(g_mutex);
		fprintf(stderr, "FAIL: pi_cond_timedwait returned %d (%s)\n",
			ret, strerror(ret));
		exit(1);
	}
	g_worker_acquired = 1;
	CHECK(pi_mutex_unlock(g_mutex) == 0);
	return NULL;
}

int main(void)
{
	pthread_t th;
	struct timespec deadline;
	int ret;

	/* Phase 1: lifecycle + uncontended fast path. */
	g_mutex = pi_mutex_alloc();
	CHECK(g_mutex != NULL);
	g_cond = pi_cond_alloc();
	CHECK(g_cond != NULL);
	CHECK(pi_mutex_init(g_mutex, 0) == 0);
	CHECK(pi_cond_init(g_cond, 0) == 0);
	CHECK(pi_mutex_trylock(g_mutex) == 0);
	CHECK(pi_mutex_unlock(g_mutex) == 0);

	/* Phase 2: contended lock forces FUTEX_LOCK_PI / FUTEX_UNLOCK_PI. */
	CHECK(pi_mutex_lock(g_mutex) == 0);
	CHECK(pthread_create(&th, NULL, contender_thread, NULL) == 0);
	msleep(200);
	CHECK(pi_mutex_unlock(g_mutex) == 0);
	CHECK(pthread_join(th, NULL) == 0);
	CHECK(g_worker_acquired == 1);
	g_worker_acquired = 0;

	/* Phase 3: condvar capability probe (no signaler).  ETIMEDOUT means
	 * the kernel implements FUTEX_WAIT_REQUEUE_PI; ENOSYS means it does
	 * not (measured platform gap on HongMeng kernel 1.12.0). */
	CHECK(pi_mutex_lock(g_mutex) == 0);
	abs_deadline(&deadline, 0);
	deadline.tv_nsec += 200 * 1000000L;
	if (deadline.tv_nsec >= 1000000000L) {
		deadline.tv_nsec -= 1000000000L;
		deadline.tv_sec += 1;
	}
	ret = pi_cond_timedwait(g_cond, g_mutex, &deadline);
	/* pi_cond_timedwait re-acquires the mutex before returning on every
	 * path (pthread_cond_timedwait semantics): 0 and ETIMEDOUT both hand
	 * the lock back to us, so release it for Phase 4's waiter thread.
	 * ENOSYS is handled separately below — there the kernel never dropped
	 * the lock, and that branch does its own unlock. */
	if (ret == 0 || ret == ETIMEDOUT)
		CHECK(pi_mutex_unlock(g_mutex) == 0);
	if (ret == ENOSYS) {
		g_cond_supported = 0;
		CHECK(pi_mutex_unlock(g_mutex) == 0);
		printf("condvar: UNSUPPORTED - kernel returns ENOSYS for "
		       "FUTEX_WAIT_REQUEUE_PI (platform capability gap)\n");
	} else if (ret != 0 && ret != ETIMEDOUT) {
		fprintf(stderr,
			"FAIL: pi_cond_timedwait probe returned %d (%s)\n",
			ret, strerror(ret));
		exit(1);
	}

	if (g_cond_supported) {
		/* Phase 4: signal wakes a parked waiter through the PI
		 * requeue path (upstream usage: pi_cond_signal does not
		 * require holding the mutex; the mutex argument identifies
		 * the requeue target). */
		CHECK(pthread_create(&th, NULL, cond_waiter_thread, NULL) == 0);
		msleep(200);
		ret = pi_cond_signal(g_cond, g_mutex);
		if (ret != 0) {
			fprintf(stderr,
				"FAIL: pi_cond_signal returned %d (%s)\n",
				ret, strerror(ret));
			exit(1);
		}
		CHECK(pthread_join(th, NULL) == 0);
		CHECK(g_worker_acquired == 1);
		g_worker_acquired = 0;

		/* Phase 5: no signaler -> ETIMEDOUT, mutex re-acquired. */
		CHECK(pi_mutex_lock(g_mutex) == 0);
		abs_deadline(&deadline, 1);
		ret = pi_cond_timedwait(g_cond, g_mutex, &deadline);
		if (ret != ETIMEDOUT) {
			fprintf(stderr,
				"FAIL: pi_cond_timedwait timeout returned %d, expected %d\n",
				ret, ETIMEDOUT);
			exit(1);
		}
		CHECK(pi_mutex_unlock(g_mutex) == 0);
	}

	/* Phase 6: teardown. */
	CHECK(pi_cond_destroy(g_cond) == 0);
	CHECK(pi_mutex_destroy(g_mutex) == 0);
	pi_cond_free(g_cond);
	pi_mutex_free(g_mutex);

	printf("librtpi test_package passed (condvar: %s)\n",
	       g_cond_supported ? "supported" : "UNSUPPORTED ENOSYS");
	return 0;
}
