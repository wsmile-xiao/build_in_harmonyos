#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <math.h>
#include "fpzip.h"

/* Round-trip test: compress a double array with fpzip_write_*, decompress
 * with fpzip_read_* and verify data equality. Uses the public fpzip API. */
int main(void) {
  const int nx = 16, ny = 8, nz = 4;
  const int n = nx * ny * nz;
  double* data = static_cast<double*>(malloc(n * sizeof(double)));
  double* back = static_cast<double*>(malloc(n * sizeof(double)));
  unsigned char* buf = static_cast<unsigned char*>(malloc(65536));
  size_t csize;
  int i, ok;

  if (!data || !back || !buf) { fprintf(stderr, "malloc failed\n"); return 1; }
  for (i = 0; i < n; i++)
    data[i] = sin(0.1 * i) + 0.001 * (i % 7);

  /* --- compress --- */
  {
    FPZ* fpz = fpzip_write_to_buffer(buf, 65536);
    if (!fpz) { fprintf(stderr, "fpzip_write_to_buffer failed\n"); return 1; }
    fpz->type = FPZIP_TYPE_DOUBLE;
    fpz->prec = 0; /* full precision */
    fpz->nx = nx; fpz->ny = ny; fpz->nz = nz; fpz->nf = 1;
    if (!fpzip_write_header(fpz)) { fprintf(stderr, "fpzip_write_header failed\n"); return 1; }
    csize = fpzip_write(fpz, data);
    if (csize == 0) { fprintf(stderr, "fpzip_write failed\n"); return 1; }
    fpzip_write_close(fpz);
  }

  /* --- decompress --- */
  {
    FPZ* fpz = fpzip_read_from_buffer(buf);
    if (!fpz) { fprintf(stderr, "fpzip_read_from_buffer failed\n"); return 1; }
    if (!fpzip_read_header(fpz)) { fprintf(stderr, "fpzip_read_header failed\n"); return 1; }
    if (fpzip_read(fpz, back) == 0) { fprintf(stderr, "fpzip_read failed\n"); return 1; }
    fpzip_read_close(fpz);
  }

  /* --- verify --- */
  ok = 1;
  for (i = 0; i < n; i++)
    if (fabs(data[i] - back[i]) > 1e-12) { ok = 0; break; }

  printf("fpzip 1.3.0 round-trip: %d doubles -> %zu bytes, verify %s\n",
         n, csize, ok ? "OK" : "FAILED");
  free(data); free(back); free(buf);
  return ok ? 0 : 1;
}
