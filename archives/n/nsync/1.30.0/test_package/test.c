/* test_package for nsync — exercises real API: mutex, condition variable,
   and a producer/consumer handoff across two threads. */
#include <pthread.h>
#include <stdio.h>

#include "nsync.h"

struct shared {
	nsync_mu mu;
	nsync_cv cv;
	int ready;
	int value;
};

static void *producer(void *arg) {
	struct shared *s = (struct shared *) arg;
	nsync_mu_lock(&s->mu);
	s->value = 42;
	s->ready = 1;
	nsync_cv_signal(&s->cv);
	nsync_mu_unlock(&s->mu);
	return NULL;
}

int main(void) {
	struct shared s;
	pthread_t th;

	s.mu = (nsync_mu) NSYNC_MU_INIT;
	s.cv = (nsync_cv) NSYNC_CV_INIT;
	s.ready = 0;
	s.value = 0;

	if (pthread_create(&th, NULL, producer, &s) != 0) {
		fprintf(stderr, "pthread_create failed\n");
		return 1;
	}

	nsync_mu_lock(&s.mu);
	while (!s.ready) {
		nsync_cv_wait(&s.cv, &s.mu);
	}
	nsync_mu_unlock(&s.mu);

	if (pthread_join(th, NULL) != 0) {
		fprintf(stderr, "pthread_join failed\n");
		return 1;
	}

	if (s.value != 42) {
		fprintf(stderr, "unexpected value: %d\n", s.value);
		return 1;
	}
	printf("nsync ok: value=%d\n", s.value);
	return 0;
}
