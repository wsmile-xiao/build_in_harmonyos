/* cond_probe.c — prove the patched .symver interposers are live.
 *
 * timer_settime()/timer_gettime() and pthread_cond_timedwait() are the two
 * families libfaketime binds to glibc version nodes; on musl/OHOS the binding
 * had to be ported. The check is timing based: with FAKETIME="-15d" an abstime
 * taken from the *faked* clock is 15 days behind the real clock, so only a
 * working interposer can wait on it — the libc implementation would return
 * ETIMEDOUT immediately.
 */
#include <errno.h>
#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

static long mono_ms(void)
{
  struct timespec ts;
  clock_gettime(CLOCK_MONOTONIC, &ts);
  return (long)(ts.tv_sec * 1000 + ts.tv_nsec / 1000000);
}

static int check_posix_timer(void)
{
  timer_t id;
  struct itimerspec its;
  memset(&its, 0, sizeof(its));
  its.it_value.tv_sec = 1;
  its.it_interval.tv_sec = 1;
  if (timer_create(CLOCK_REALTIME, NULL, &id) != 0) { perror("timer_create"); return 1; }
  if (timer_settime(id, 0, &its, NULL) != 0) { perror("timer_settime"); return 1; }

  struct itimerspec out;
  if (timer_gettime(id, &out) != 0)
  {
    perror("timer_gettime");
    return 1;
  }
  printf("timer_gettime() armed -> value %ld.%09ld\n",
         (long)out.it_value.tv_sec, out.it_value.tv_nsec);
  if (out.it_value.tv_sec < 0 || out.it_value.tv_sec > 2)
  {
    fprintf(stderr, "cond_probe: timer_gettime returned an out-of-range remaining time\n");
    return 1;
  }
  timer_delete(id);
  return 0;
}

static int check_cond_timedwait(void)
{
  pthread_cond_t cond = PTHREAD_COND_INITIALIZER;
  pthread_mutex_t mutex = PTHREAD_MUTEX_INITIALIZER;
  struct timespec deadline;

  /* Start from the faked wall clock, i.e. 15 days behind reality. */
  if (clock_gettime(CLOCK_REALTIME, &deadline) != 0) { perror("clock_gettime"); return 1; }
  deadline.tv_sec += 1;

  pthread_mutex_lock(&mutex);
  long started = mono_ms();
  int rc = pthread_cond_timedwait(&cond, &mutex, &deadline);
  long waited = mono_ms() - started;
  pthread_mutex_unlock(&mutex);

  printf("pthread_cond_timedwait() rc=%d (%s), waited %ld ms\n",
         rc, rc == ETIMEDOUT ? "ETIMEDOUT" : (rc == 0 ? "signalled" : strerror(rc)), waited);
  if (rc != ETIMEDOUT)
  {
    fprintf(stderr, "cond_probe: expected ETIMEDOUT from a never-signalled condition\n");
    return 1;
  }
  /* Without interposition the deadline is 15 days in the past -> ~0 ms wait. */
  if (waited < 800)
  {
    fprintf(stderr, "cond_probe: waited only %ld ms; pthread_cond_timedwait is not "
                    "honouring the faked CLOCK_REALTIME\n", waited);
    return 1;
  }
  return 0;
}

int main(void)
{
  if (check_posix_timer() != 0) return 1;
  if (check_cond_timedwait() != 0) return 1;
  printf("cond_probe: OK\n");
  return 0;
}
