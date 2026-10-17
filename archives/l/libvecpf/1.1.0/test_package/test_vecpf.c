/* test_vecpf.c - consumer test for libvecpf on OpenHarmony / musl.
 *
 * Exercises the public API exported by the shared library through the
 * installed header <vecpf.h>.  Every expected value below is computed by
 * hand from the byte layout of the test vectors, not by copying whatever the
 * library happens to print.
 *
 * Exit status: 0 when every case matches, 1 otherwise.
 */

#include <pthread.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

#include <vecpf.h>

static int failures;
static int checks;

#define VEC_INT_EXPECTED "287454020 1432778632 -1430532899 -559038737"

/* Resident set size in kB, or -1 when it cannot be determined. */
static long
rss_kb (void)
{
  FILE *f = fopen ("/proc/self/statm", "r");
  long total = 0, resident = 0;

  if (f == NULL)
    return -1;
  if (fscanf (f, "%ld %ld", &total, &resident) != 2)
    {
      fclose (f);
      return -1;
    }
  fclose (f);
  (void) total;
  return resident * (long) (sysconf (_SC_PAGESIZE) / 1024);
}

/* Each thread formats the same vector many times.  The library must keep its
   scratch state per-thread; a process-wide buffer would race here. */
static void *
vecpf_worker (void *arg)
{
  const vp_u_t *u = (const vp_u_t *) arg;
  char local[128];
  int i;

  for (i = 0; i < 20000; i++)
    {
      if (vecpf_sprintf (local, "%vld", u->v) < 0)
        return (void *) 1;
      if (strcmp (local, VEC_INT_EXPECTED) != 0)
        return (void *) 1;
    }
  return NULL;
}

static void
check (const char *name, const char *actual, const char *expected)
{
  checks++;
  if (strcmp (actual, expected) != 0)
    {
      printf ("FAIL %-22s expected \"%s\" but got \"%s\"\n", name, expected, actual);
      failures++;
    }
  else
    {
      printf ("ok   %-22s \"%s\"\n", name, actual);
    }
}

int
main (void)
{
  vp_u_t u;
  char buf[512];
  int n;

  /* ---- 16-byte test vector: four 32-bit words ---------------------------
     little-endian byte order: 44 33 22 11 | 88 77 66 55 | DD CC BB AA | EF BE AD DE */
  u.ui[0] = 0x11223344u;
  u.ui[1] = 0x55667788u;
  u.ui[2] = 0xaabbccddu;
  u.ui[3] = 0xdeadbeefu;

  vecpf_sprintf (buf, "%vld", u.v);
  check ("%vld (4x int32)", buf, "287454020 1432778632 -1430532899 -559038737");

  vecpf_sprintf (buf, "%vlx", u.v);
  check ("%vlx (4x hex32)", buf, "11223344 55667788 aabbccdd deadbeef");

  vecpf_sprintf (buf, "%012vlx", u.v);
  check ("%012vlx (zero pad)", buf,
         "000011223344 000055667788 0000aabbccdd 0000deadbeef");

  vecpf_sprintf (buf, "%vhu", u.v);
  check ("%vhu (8x uint16)", buf,
         "13124 4386 30600 21862 52445 43707 48879 57005");

  /* 16 signed bytes of the same vector */
  vecpf_sprintf (buf, "%vd", u.v);
  check ("%vd (16x int8)", buf,
         "68 51 34 17 -120 119 102 85 -35 -52 -69 -86 -17 -66 -83 -34");

  /* ---- four single-precision lanes ------------------------------------- */
  u.f[0] = 1.5f;
  u.f[1] = 2.5f;
  u.f[2] = -3.25f;
  u.f[3] = 0.0f;

  vecpf_sprintf (buf, "%vf", u.v);
  check ("%vf (4x float)", buf, "1.500000 2.500000 -3.250000 0.000000");

  /* ---- two double-precision lanes -------------------------------------- */
  u.d[0] = 1.25;
  u.d[1] = -2.5;

  vecpf_sprintf (buf, "%vvf", u.v);
  check ("%vvf (2x double)", buf, "1.250000 -2.500000");

  /* ---- back to the integer vector, then test the return-value contract --- */
  u.ui[0] = 0x11223344u;
  u.ui[1] = 0x55667788u;
  u.ui[2] = 0xaabbccddu;
  u.ui[3] = 0xdeadbeefu;

  {
    const char *exp = "287454020 1432778632 -1430532899 -559038737";
    n = vecpf_sprintf (buf, "%vld", u.v);
    check ("%vld return value",
           (n == (int) strlen (exp) && strcmp (buf, exp) == 0) ? "match" : "mismatch",
           "match");
  }

  /* ---- non-vector conversions must still work --------------------------- */
  vecpf_sprintf (buf, "n=%d s=%s f=%.2f x=%#x c=%c", 42, "ok", 3.14159, 255u, 'Z');
  check ("plain conversions", buf, "n=42 s=ok f=3.14 x=0xff c=Z");

  /* ---- vecpf_asprintf --------------------------------------------------- */
  {
    char *s = vecpf_asprintf ("[%vlx]", u.v);
    check ("vecpf_asprintf", s ? s : "(null)", "[11223344 55667788 aabbccdd deadbeef]");
    free (s);
  }

  /* ---- a field wider than any internal line buffer must not be truncated --
     Four lanes at width 1100 plus the three separating spaces = 4403 chars. */
  {
    const size_t want = 4 * 1100 + 3;
    char *big = (char *) malloc (want + 8);

    if (big == NULL)
      {
        printf ("FAIL %-22s could not allocate\n", "wide field");
        failures++;
        checks++;
      }
    else
      {
        u.ui[0] = 1u; u.ui[1] = 2u; u.ui[2] = 3u; u.ui[3] = 4u;
        n = vecpf_sprintf (big, "%1100vlu", u.v);
        check ("wide field (1100)",
               (n == (int) want && strlen (big) == want && big[0] == ' '
                && big[want - 1] == '4') ? "intact" : "truncated",
               "intact");
        free (big);
      }
  }

  /* ---- vecpf_fprintf writes through a real FILE* ------------------------ */
  {
    FILE *fp = fopen ("vecpf_fprintf_out.txt", "w");
    if (fp == NULL)
      {
        printf ("FAIL vecpf_fprintf        could not open output file\n");
        failures++;
        checks++;
      }
    else
      {
        u.ui[0] = 1u; u.ui[1] = 2u; u.ui[2] = 3u; u.ui[3] = 4u;
        vecpf_fprintf (fp, "%vld", u.v);
        fclose (fp);

        fp = fopen ("vecpf_fprintf_out.txt", "r");
        if (fp == NULL || fgets (buf, sizeof (buf), fp) == NULL)
          {
            printf ("FAIL vecpf_fprintf        could not read back\n");
            failures++;
            checks++;
          }
        else
          {
            buf[strcspn (buf, "\n")] = '\0';
            check ("vecpf_fprintf (FILE*)", buf, "1 2 3 4");
          }
        if (fp != NULL)
          fclose (fp);
      }
  }

  /* ---- repeated calls must not accumulate memory ------------------------
     The front-end used to hand the scratch buffer to nobody on the sprintf
     path; at ~132 bytes per call, 200000 calls grew RSS by ~26 MB. */
  {
    long before = rss_kb ();
    int i, ok = 1;

    if (before < 0)
      {
        printf ("skip %-22s /proc/self/statm unavailable\n", "no leak (200k calls)");
      }
    else
      {
        u.ui[0] = 0x11223344u; u.ui[1] = 0x55667788u;
        u.ui[2] = 0xaabbccddu; u.ui[3] = 0xdeadbeefu;

        for (i = 0; i < 200000 && ok; i++)
          {
            vecpf_sprintf (buf, "%vld", u.v);
            if (strcmp (buf, VEC_INT_EXPECTED) != 0)
              ok = 0;
          }

        {
          long growth = rss_kb () - before;

          checks++;
          if (ok && growth < 512)
            printf ("ok   %-22s RSS +%ld kB over 200000 calls\n",
                    "no leak (200k calls)", growth);
          else
            {
              printf ("FAIL %-22s RSS +%ld kB (correct=%d)\n",
                      "no leak (200k calls)", growth, ok);
              failures++;
            }
        }
      }
  }

  /* ---- concurrent use must not corrupt the scratch state --------------- */
  {
    pthread_t th[4];
    int i, made = 0, bad = 0;

    for (i = 0; i < 4; i++)
      if (pthread_create (&th[i], NULL, vecpf_worker, &u) == 0)
        made++;

    if (made == 4)
      {
        for (i = 0; i < 4; i++)
          {
            void *rc = NULL;
            pthread_join (th[i], &rc);
            if (rc != NULL)
              bad++;
          }
        check ("4-thread concurrency", bad == 0 ? "clean" : "corrupt", "clean");
      }
    else
      {
        for (i = 0; i < made; i++)
          pthread_join (th[i], NULL);
        printf ("skip %-22s pthread_create failed\n", "4-thread concurrency");
      }
  }

  printf ("\n%d/%d checks passed\n", checks - failures, checks);
  return failures != 0;
}
