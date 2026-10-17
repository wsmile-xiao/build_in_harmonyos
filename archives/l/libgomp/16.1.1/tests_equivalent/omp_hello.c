/* Equivalent rewrite: #pragma omp parallel private(nthreads,tid) -> GOMP_parallel */
#include <omp.h>
#include "libgomp_g.h"
#include <stdio.h>

static void
hello_body (void *data)
{
  int nthreads, tid;
  (void) data;

  tid = omp_get_thread_num ();
  printf ("Hello World from thread = %d\n", tid);

  if (tid == 0)
    {
      nthreads = omp_get_num_threads ();
      printf ("Number of threads = %d\n", nthreads);
    }
}

int
main (int argc, char *argv[])
{
  (void) argc; (void) argv;
  GOMP_parallel (hello_body, NULL, 0, 0);
  return 0;
}
