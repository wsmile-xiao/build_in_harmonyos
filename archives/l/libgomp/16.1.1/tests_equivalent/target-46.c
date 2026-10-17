/* dg-shouldfail "omp_invalid_device" - host-only equivalent.  */
#include <omp.h>
#include <stdlib.h>
#include <unistd.h>
#include <sys/wait.h>

void GOMP_target (int, void (*)(void *), const void *, size_t, void **, size_t *, unsigned char *);

static void
body (void *d)
{
  (void) d;
}

volatile int dev = omp_invalid_device;

int
main ()
{
  pid_t pid = fork ();
  if (pid == 0)
    {
      /* target device(dev) where dev == omp_invalid_device */
      GOMP_target (dev, body, NULL, 0, NULL, NULL, NULL);
      _exit (0);
    }
  int st = 0;
  waitpid (pid, &st, 0);
  if (!WIFEXITED (st) || WEXITSTATUS (st) == 0)
    abort ();
  return 0;
}
