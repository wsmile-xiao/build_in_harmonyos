/* dg-shouldfail "omp_invalid_device" - host-only equivalent: verify the
   omp_invalid_device fatal error is raised, and report success (rc=0).  */
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

int
main ()
{
  pid_t pid = fork ();
  if (pid == 0)
    {
      /* target device(omp_invalid_device) */
      GOMP_target (omp_invalid_device, body, NULL, 0, NULL, NULL, NULL);
      _exit (0);
    }
  int st = 0;
  waitpid (pid, &st, 0);
  if (!WIFEXITED (st) || WEXITSTATUS (st) == 0)
    abort ();
  return 0;
}
