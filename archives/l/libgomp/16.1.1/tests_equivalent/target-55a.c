/* dg-shouldfail "omp_invalid_device" (OMP_TARGET_OFFLOAD=mandatory, no device).
   Host-only equivalent: verify the mandatory fatal error.  */
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
      GOMP_target (-1, body, NULL, 0, NULL, NULL, NULL);
      _exit (0);
    }
  int st = 0;
  waitpid (pid, &st, 0);
  if (!WIFEXITED (st) || WEXITSTATUS (st) == 0)
    abort ();
  return 0;
}
