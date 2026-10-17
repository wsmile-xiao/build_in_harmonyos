/*
 * test_target.c — stdin-processing "fuzz target" for the test_package.
 *
 * The packaged AFL++ tools genuinely drive this program in test():
 * afl-clang-fast instruments it (LLVM passes from lib/afl), afl-showmap
 * captures its coverage map, afl-fuzz mutates its input. It has an
 * input-dependent rare branch (first byte 'X') so different seeds yield
 * different coverage maps — proving instrumentation really works.
 */
#include <stdio.h>

int main(void) {

  unsigned long acc = 5381;
  size_t        len = 0;
  int           c;

  while ((c = getchar()) != EOF) {

    acc = acc * 33 + (unsigned char)c;

    /* Rare edge — only reachable when the first byte is 'X'. */
    if (len == 0 && c == 'X') acc ^= 0x5bd1e995;

    len++;
    if (len > 4096) break;

  }

  /* Deterministic digest so the optimizer cannot remove the work. */
  fprintf(stderr, "digest=%lx len=%zu\n", acc, len);
  return 0;

}
