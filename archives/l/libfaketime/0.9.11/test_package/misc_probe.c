/* misc_probe.c — exercise the FAKE_PID / FAKE_RANDOM opt-in interceptors.
 *
 * Both features are compile-time switches upstream (-DFAKE_PID / -DFAKE_RANDOM)
 * and are driven purely from the environment, which makes them directly
 * observable from a consumer process:
 *
 *   --pid            getpid() must return the value of FAKETIME_FAKEPID
 *   --random <file>  dump 16 getrandom() bytes as hex into <file> so the caller
 *                    can compare runs: with FAKERANDOM_SEED set the stream must
 *                    be identical across processes, without it two reads inside
 *                    one process must differ (real kernel entropy).
 *
 * Note on the seed: fakerandom_msws() yields ((i * seed) >> 32) & 0xFF for the
 * i-th byte, so a 16-byte read is all zero unless seed >= 2^28 (measured:
 * 1 / 20260925 / 20260926 -> 16 zero bytes).  The driver therefore uses the
 * same 64-bit hex seed convention as upstream's own getrandom.variable test
 * expectation, and nothing here asserts "non-zero" — the contract under test is
 * reproducibility across processes.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/random.h>
#include <unistd.h>

#define N 16

static int dump_random(const char *outfile)
{
  unsigned char a[N], b[N];

  if (getrandom(a, sizeof a, 0) != (ssize_t)sizeof a) { perror("getrandom"); return 1; }
  if (getentropy(b, sizeof b) != 0) { perror("getentropy"); return 1; }

  FILE *f = fopen(outfile, "w");
  if (f == NULL) { perror(outfile); return 1; }
  for (int i = 0; i < N; i++) fprintf(f, "%02x", a[i]);
  fputc('\n', f);
  fclose(f);

  if (getenv("FAKERANDOM_SEED") == NULL)
  {
    /* Unseeded: the two fresh reads above came from the kernel, and 16 bytes of
     * real entropy repeating would mean the fake path was taken by mistake. */
    if (memcmp(a, b, sizeof a) == 0)
    {
      fprintf(stderr, "misc_probe: unseeded getrandom()/getentropy() returned the same bytes\n");
      return 1;
    }
    printf("unseeded: getrandom != getentropy (real entropy)\n");
  }
  else
  {
    printf("seeded  : FAKERANDOM_SEED=%s -> %s\n", getenv("FAKERANDOM_SEED"), outfile);
  }
  return 0;
}

int main(int argc, char **argv)
{
  if (argc >= 2 && !strcmp(argv[1], "--pid"))
  {
    const char *fakepid = getenv("FAKETIME_FAKEPID");
    if (fakepid == NULL)
    {
      fprintf(stderr, "misc_probe: FAKETIME_FAKEPID not set\n");
      return 2;
    }
    pid_t want = (pid_t)strtol(fakepid, NULL, 0);
    pid_t got = getpid();
    printf("getpid() = %d (want %d)\n", (int)got, (int)want);
    if (got != want)
    {
      fprintf(stderr, "misc_probe: FAKE_PID interposer not active\n");
      return 1;
    }
    return 0;
  }

  if (argc >= 4 && !strcmp(argv[1], "--random"))
  {
    if (!strcmp(argv[2], "--seed")) return dump_random(argv[3]);
    fprintf(stderr, "misc_probe: expected --seed <file>\n");
    return 2;
  }

  fprintf(stderr, "misc_probe: usage: --pid | --random --seed <file>\n");
  return 2;
}
