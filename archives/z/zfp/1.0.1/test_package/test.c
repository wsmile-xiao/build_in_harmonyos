#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "zfp.h"

int main(void)
{
  const size_t nx = 8;
  const size_t ny = 4;
  const size_t nz = 2;
  const size_t count = nx * ny * nz;
  const size_t bytes = count * sizeof(double);
  double* source = NULL;
  double* decoded = NULL;
  unsigned char* buffer = NULL;
  zfp_field* field = NULL;
  zfp_stream* zfp = NULL;
  bitstream* stream = NULL;
  size_t buffer_size;
  size_t compressed_size;
  int result = EXIT_FAILURE;

  source = (double*)malloc(bytes);
  decoded = (double*)calloc(count, sizeof(double));
  if (!source || !decoded) {
    fprintf(stderr, "allocation failed\n");
    goto cleanup;
  }

  for (size_t i = 0; i < count; ++i)
    source[i] = (double)(i * 3) / 7.0 - 2.5;

  field = zfp_field_3d(source, zfp_type_double, nx, ny, nz);
  zfp = zfp_stream_open(NULL);
  if (!field || !zfp) {
    fprintf(stderr, "zfp metadata allocation failed\n");
    goto cleanup;
  }

  zfp_stream_set_reversible(zfp);
  buffer_size = zfp_stream_maximum_size(zfp, field);
  buffer = (unsigned char*)malloc(buffer_size);
  if (!buffer) {
    fprintf(stderr, "compressed buffer allocation failed\n");
    goto cleanup;
  }

  stream = stream_open(buffer, buffer_size);
  if (!stream) {
    fprintf(stderr, "bitstream allocation failed\n");
    goto cleanup;
  }
  zfp_stream_set_bit_stream(zfp, stream);
  zfp_stream_rewind(zfp);

  compressed_size = zfp_compress(zfp, field);
  if (!compressed_size) {
    fprintf(stderr, "compression failed\n");
    goto cleanup;
  }

  zfp_field_set_pointer(field, decoded);
  zfp_stream_rewind(zfp);
  if (!zfp_decompress(zfp, field)) {
    fprintf(stderr, "decompression failed\n");
    goto cleanup;
  }

  if (memcmp(source, decoded, bytes) != 0) {
    fprintf(stderr, "reversible round-trip mismatch\n");
    goto cleanup;
  }

  printf("zfp round-trip: version=%s compressed=%zu bytes values=%zu\n",
         zfp_version_string, compressed_size, count);
  result = EXIT_SUCCESS;

cleanup:
  if (field)
    zfp_field_free(field);
  if (zfp)
    zfp_stream_close(zfp);
  if (stream)
    stream_close(stream);
  free(buffer);
  free(decoded);
  free(source);
  return result;
}
