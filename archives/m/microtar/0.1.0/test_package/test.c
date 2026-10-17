/* microtar consumer test: write a tar archive, read it back and verify contents.
 * Exercises the real microtar API: mtar_open/write_file_header/write_data/
 * finalize/close and read_header/read_data/next.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <microtar.h>

static int test_write_read(void) {
  mtar_t tar;
  const char *str1 = "Hello world";
  const char *str2 = "Goodbye world";
  mtar_header_t h;
  char buf[256];
  int rc;

  /* write phase */
  if ((rc = mtar_open(&tar, "test.tar", "w")) != MTAR_ESUCCESS) return 1;
  if ((rc = mtar_write_file_header(&tar, "test1.txt", (unsigned)strlen(str1))) != MTAR_ESUCCESS) return 2;
  if ((rc = mtar_write_data(&tar, str1, (unsigned)strlen(str1))) != MTAR_ESUCCESS) return 3;
  if ((rc = mtar_write_file_header(&tar, "test2.txt", (unsigned)strlen(str2))) != MTAR_ESUCCESS) return 4;
  if ((rc = mtar_write_data(&tar, str2, (unsigned)strlen(str2))) != MTAR_ESUCCESS) return 5;
  if ((rc = mtar_finalize(&tar)) != MTAR_ESUCCESS) return 6;
  mtar_close(&tar);

  /* read phase: header -> data -> next loop until ENULLRECORD */
  if ((rc = mtar_open(&tar, "test.tar", "r")) != MTAR_ESUCCESS) return 7;
  if ((rc = mtar_read_header(&tar, &h)) != MTAR_ESUCCESS) return 8;
  if (strcmp(h.name, "test1.txt") != 0 || h.size != strlen(str1)) return 9;
  memset(buf, 0, sizeof(buf));
  if ((rc = mtar_read_data(&tar, buf, h.size)) != MTAR_ESUCCESS) return 10;
  if (strcmp(buf, str1) != 0) return 11;
  if ((rc = mtar_next(&tar)) != MTAR_ESUCCESS) return 12;
  if ((rc = mtar_read_header(&tar, &h)) != MTAR_ESUCCESS) return 13;
  if (strcmp(h.name, "test2.txt") != 0 || h.size != strlen(str2)) return 14;
  memset(buf, 0, sizeof(buf));
  if ((rc = mtar_read_data(&tar, buf, h.size)) != MTAR_ESUCCESS) return 15;
  if (strcmp(buf, str2) != 0) return 16;
  if ((rc = mtar_next(&tar)) != MTAR_ESUCCESS) return 17;
  if ((rc = mtar_read_header(&tar, &h)) != MTAR_ENULLRECORD) return 18;
  mtar_close(&tar);
  return 0;
}

int main(void) {
  int rc = test_write_read();
  if (rc != 0) {
    printf("FAIL: microtar test step %d (%s)\n", rc, mtar_strerror(rc));
    return 1;
  }
  printf("PASS: microtar write/read round-trip ok\n");
  return 0;
}
