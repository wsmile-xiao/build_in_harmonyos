/*
 * Consumer test for libpd 0.16.1 — exercises the installed library through
 * its public C API (z_libpd.h): initialization, version banner, patch
 * loading, message round trip via a bound receiver, and real DSP
 * processing of a [osc~] -> [dac~] signal chain.
 *
 * Exits non-zero if any assertion fails.  The fixture patch is
 * libpdtest.pd, passed as argv[1] with its directory as argv[2].
 */
#include <math.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "z_libpd.h"

#define BLOCK_SIZE 64
#define OUT_CHANNELS 2
#define PRINT_BUFFER 8192

static char print_buffer[PRINT_BUFFER];
static size_t print_length = 0;
static int failures = 0;

static void capture_print(const char *s) {
  size_t n = strlen(s);
  if (print_length + n + 1 < PRINT_BUFFER) {
    memcpy(print_buffer + print_length, s, n);
    print_length += n;
    print_buffer[print_length] = '\0';
  }
}

static void check(int condition, const char *what) {
  printf("%s: %s\n", condition ? "PASS" : "FAIL", what);
  if (!condition) {
    failures++;
  }
}

int main(int argc, char **argv) {
  const char *patch = argc > 1 ? argv[1] : "libpdtest.pd";
  const char *folder = argc > 2 ? argv[2] : ".";
  const int sample_rate = 44100;
  float inbuf[BLOCK_SIZE];
  float outbuf[BLOCK_SIZE * OUT_CHANNELS];
  float peak = 0.0f;
  int i, j, finite = 1;
  void *handle;

  libpd_set_printhook(capture_print);

  check(libpd_init() == 0, "libpd_init() returns 0");
  check(strncmp(print_buffer, "pd ", 3) == 0,
        "libpd_init() posts the Pure Data version banner");
  /* Fingerprint of the pure-data snapshot pinned by libpd 0.16.1. */
  check(strstr(print_buffer, "0.56.5") != NULL,
        "the vendored pure-data snapshot is the pinned 0.56.5 revision");

  check(libpd_init_audio(1, OUT_CHANNELS, sample_rate) == 0,
        "libpd_init_audio() accepts the test configuration");
  check(libpd_blocksize() == BLOCK_SIZE, "libpd_blocksize() is 64");

  handle = libpd_openfile(patch, folder);
  check(handle != NULL, "libpd_openfile() opens the fixture patch");
  check(handle != NULL && libpd_getdollarzero(handle) > 0,
        "the loaded patch has a valid dollar-zero");
  check(libpd_exists("libpdtest") == 1,
        "the fixture receiver is registered after loading the patch");

  /* [r libpdtest] -> [msg 42] -> [print libpdtest] */
  check(libpd_bang("libpdtest") == 0, "libpd_bang() reaches the receiver");
  check(strstr(print_buffer, "libpdtest: 42") != NULL,
        "the message round trip prints the expected value");
  /* [r libpdtestfloat] -> [print libpdtestfloat] */
  check(libpd_float("libpdtestfloat", 3.5f) == 0,
        "libpd_float() reaches the receiver");
  check(strstr(print_buffer, "libpdtestfloat: 3.5") != NULL,
        "the float round trip prints the expected value");

  /* [; pd dsp 1( then process a [osc~ 440] -> [dac~] chain. */
  libpd_start_message(1);
  libpd_add_float(1.0f);
  check(libpd_finish_message("pd", "dsp") == 0, "DSP can be enabled");
  memset(inbuf, 0, sizeof(inbuf));
  for (i = 0; i < 100; i++) {
    libpd_process_float(1, inbuf, outbuf);
    for (j = 0; j < BLOCK_SIZE * OUT_CHANNELS; j++) {
      float sample = outbuf[j];
      if (!isfinite(sample)) {
        finite = 0;
      }
      if (fabsf(sample) > peak) {
        peak = fabsf(sample);
      }
    }
  }
  check(finite, "DSP output samples are finite");
  check(peak > 0.1f, "the [osc~ 440] chain produces audible signal");
  check(peak <= 1.0f, "the DSP output stays within [-1, 1]");

  if (handle != NULL) {
    libpd_closefile(handle);
  }
  printf("failures=%d\n", failures);
  return failures == 0 ? 0 : 1;
}
