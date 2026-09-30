/* test_vecpf_cxx.cpp - C++ consumer check for libvecpf on OHOS/musl.
 *
 * libvecpf is a C library.  Its public header must therefore declare the entry
 * points with C linkage; without an `extern "C"` guard the C++ compiler mangles
 * the names and linking against the C library fails with
 *
 *     ld.lld: error: undefined symbol: vecpf_sprintf(char*, char const*, ...)
 *     >>> did you mean: extern "C" vecpf_sprintf
 *
 * This file exists so that regression is caught by `conan create`.
 *
 * Exit status: 0 when every case matches, 1 otherwise.
 */

#include <cstdio>
#include <cstdlib>
#include <cstring>

#include <vecpf.h>

int
main ()
{
  vp_u_t u;
  char buf[128];
  int failures = 0;

  u.ui[0] = 0x11223344u;
  u.ui[1] = 0x55667788u;
  u.ui[2] = 0xaabbccddu;
  u.ui[3] = 0xdeadbeefu;

  if (vecpf_sprintf (buf, "%vlx", u.v) <= 0
      || std::strcmp (buf, "11223344 55667788 aabbccdd deadbeef") != 0)
    {
      std::printf ("FAIL %-22s got \"%s\"\n", "c++ vecpf_sprintf", buf);
      failures++;
    }
  else
    {
      std::printf ("ok   %-22s \"%s\"\n", "c++ vecpf_sprintf", buf);
    }

  char *s = vecpf_asprintf ("%vld", u.v);
  if (s == NULL
      || std::strcmp (s, "287454020 1432778632 -1430532899 -559038737") != 0)
    {
      std::printf ("FAIL %-22s got \"%s\"\n", "c++ vecpf_asprintf", s ? s : "(null)");
      failures++;
    }
  else
    {
      std::printf ("ok   %-22s \"%s\"\n", "c++ vecpf_asprintf", s);
    }
  std::free (s);

  std::printf ("c++ consumer: %d failure(s)\n", failures);
  return failures != 0;
}
