/* clock_probe.c — assert the three wall-clock APIs agree with an expected epoch.
 *
 * Driven under LD_PRELOAD: the caller computes --expect from an unfaked process,
 * so if libfaketime does not interpose, every reading is off by the whole offset.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/time.h>
#include <time.h>

int main(int argc, char **argv)
{
  long expect = -1;
  long tol = 5;
  for (int i = 1; i < argc; i++)
  {
    if (!strcmp(argv[i], "--expect") && i + 1 < argc) expect = atol(argv[++i]);
    else if (!strcmp(argv[i], "--tol") && i + 1 < argc) tol = atol(argv[++i]);
  }
  if (expect < 0)
  {
    fprintf(stderr, "clock_probe: usage: --expect <epoch> [--tol <sec>]\n");
    return 2;
  }

  int bad = 0;
  time_t t = time(NULL);
  struct timespec ts;
  if (clock_gettime(CLOCK_REALTIME, &ts) != 0) { perror("clock_gettime"); return 1; }
  struct timeval tv;
  if (gettimeofday(&tv, NULL) != 0) { perror("gettimeofday"); return 1; }

  long d;
  d = (long)(t - expect); if (d < 0) d = -d;
  printf("time()          = %lld (|delta|=%ld)\n", (long long)t, d);
  if (d > tol) bad++;

  d = (long)(ts.tv_sec - expect); if (d < 0) d = -d;
  printf("clock_gettime() = %lld (|delta|=%ld)\n", (long long)ts.tv_sec, d);
  if (d > tol) bad++;

  d = (long)(tv.tv_sec - expect); if (d < 0) d = -d;
  printf("gettimeofday()  = %lld (|delta|=%ld)\n", (long long)tv.tv_sec, d);
  if (d > tol) bad++;

  if (bad) { fprintf(stderr, "clock_probe: %d API(s) out of tolerance\n", bad); return 1; }
  printf("clock_probe: OK\n");
  return 0;
}
