/* Equivalent rewrite: orphaned "single copyprivate(a) copyprivate(b)".
 * copyprivate is modeled as single_start + explicit barrier + broadcast buffer. */
#include <omp.h>
#include "libgomp_g.h"
#include <stdlib.h>

struct cp3_data
{
  int a;
  int b;
};

static struct cp3_data s3_buf;   /* broadcast buffer; one single region, so a static is safe */

static void
single (int a, int b)
{
  if (GOMP_single_start ())
    {
      a = b = 5;
      s3_buf.a = a;
      s3_buf.b = b;
    }
  GOMP_barrier ();

  a = s3_buf.a;
  b = s3_buf.b;

  if (a != b)
    abort ();
}

static void
par_body (void *data)
{
  (void) data;
  single (1, 2);
}

int
main ()
{
  GOMP_parallel (par_body, NULL, 0, 0);
  return 0;
}
