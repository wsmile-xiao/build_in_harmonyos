#include <sys/stat.h>
#include <sys/types.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <getdata.h>

static int write_file(const char *path, const void *data, size_t len)
{
  FILE *f = fopen(path, "wb");
  if (!f)
    return -1;
  if (len && fwrite(data, 1, len, f) != len) {
    fclose(f);
    return -1;
  }
  fclose(f);
  return 0;
}

int main(void)
{
  const char *dir = "test_dirfile";
  const char *format_path = "test_dirfile/format";
  const char *raw_path = "test_dirfile/data";
  unsigned char written[16];
  unsigned char out[8];
  DIRFILE *d = NULL;
  int n = 0;
  int error = 0;
  int i;
  int checks_passed = 0;

  for (i = 0; i < 16; ++i)
    written[i] = (unsigned char)(40 + i);
  memset(out, 0, sizeof(out));

  (void)system("rm -rf test_dirfile");
  if (mkdir(dir, 0700) != 0) {
    fprintf(stderr, "mkdir failed\n");
    return 1;
  }
  if (write_file(format_path, "data RAW UINT8 1\n", strlen("data RAW UINT8 1\n")) != 0) {
    fprintf(stderr, "format write failed\n");
    return 1;
  }
  if (write_file(raw_path, written, sizeof(written)) != 0) {
    fprintf(stderr, "raw write failed\n");
    return 1;
  }

  /* Check 1: open the dirfile and read 8 bytes starting at frame 5. */
  d = gd_open(dir, GD_RDONLY | GD_VERBOSE);
  if (d == NULL) {
    fprintf(stderr, "gd_open failed\n");
    return 1;
  }
  n = gd_getdata(d, "data", 5, 0, 8, 0, GD_UINT8, out);
  error = gd_error(d);
  if (error != 0 || n != 8) {
    fprintf(stderr, "gd_getdata n=%d error=%d\n", n, error);
    gd_discard(d);
    return 1;
  }
  for (i = 0; i < 8; ++i) {
    if (out[i] != (unsigned char)(45 + i)) {
      fprintf(stderr, "data mismatch at %d: %u\n", i, out[i]);
      gd_discard(d);
      return 1;
    }
  }
  checks_passed++;
  printf("check1 gd_getdata ok\n");

  /* Check 2: field count and standards query on the open dirfile.
     gd_nfields() counts all entries including the implicit INDEX field,
     so this dirfile (INDEX + "data") reports 2. gd_dirfile_standards()
     with GD_VERSION_CURRENT only reports: success returns the current
     Standards Version (0..GD_DIRFILE_STANDARDS_VERSION, 10 in 0.11.0),
     failure returns a negative error code. */
  {
    unsigned int nfields = gd_nfields(d);
    int v = gd_dirfile_standards(d, GD_VERSION_CURRENT);
    printf("gd_nfields=%u standards=%d\n", nfields, v);
    if (nfields < 2 || v < 0) {
      fprintf(stderr, "gd_nfields=%u standards=%d\n", nfields, v);
      gd_discard(d);
      return 1;
    }
  }
  checks_passed++;
  printf("check2 metadata ok\n");

  /* Check 3: clean close reports no error. */
  error = gd_close(d);
  if (error != 0) {
    fprintf(stderr, "gd_close error=%d\n", error);
    return 1;
  }
  checks_passed++;
  printf("check3 gd_close ok\n");

  (void)system("rm -rf test_dirfile");
  if (checks_passed != 3) {
    fprintf(stderr, "only %d/3 checks passed\n", checks_passed);
    return 1;
  }
  printf("libgetdata test_package: 3/3 checks passed\n");
  return 0;
}
