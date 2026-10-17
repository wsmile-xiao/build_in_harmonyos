/*
 * Consumer test for libaudec 0.3.4 on OHOS (HarmonyOS PC).
 *
 * Synthesizes a 16-bit PCM WAV (mono, 48 kHz, 16000 frames of a 440 Hz
 * sine), then exercises the public decoder API as a real consumer:
 * audec_finfo / audec_open / audec_read (identity pass and a libsamplerate
 * down-sample) / audec_close / audec_free_nfo.
 *
 * Exactly 12 checked assertions; exits 0 only if every one passes.
 * The expected resampled frame count mirrors upstream's own oracle
 * (tests/test.c: expected_frames_after = frames * target_rate / rate).
 */
#include <math.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <audec/audec.h>

#define SAMPLE_RATE 48000u
#define FRAMES      16000
#define FREQ        440.0

static int failures = 0;

#define CHECK(cond, msg)                       \
    do {                                       \
        if (cond) {                            \
            printf ("PASS: %s\n", msg);        \
        } else {                               \
            printf ("FAIL: %s\n", msg);        \
            failures++;                        \
        }                                      \
    } while (0)

static void
put_u32 (uint8_t * p, uint32_t v)
{
  p[0] = (uint8_t) (v & 0xff);
  p[1] = (uint8_t) ((v >> 8) & 0xff);
  p[2] = (uint8_t) ((v >> 16) & 0xff);
  p[3] = (uint8_t) ((v >> 24) & 0xff);
}

static void
put_u16 (uint8_t * p, uint16_t v)
{
  p[0] = (uint8_t) (v & 0xff);
  p[1] = (uint8_t) ((v >> 8) & 0xff);
}

static int
write_wav (const char * path)
{
  const uint32_t data_size = (uint32_t) FRAMES * 2u; /* 16-bit mono */
  uint8_t hdr[44];
  FILE * f;
  uint32_t i;

  memcpy (&hdr[0], "RIFF", 4);
  put_u32 (&hdr[4], 36u + data_size);
  memcpy (&hdr[8], "WAVE", 4);
  memcpy (&hdr[12], "fmt ", 4);
  put_u32 (&hdr[16], 16u);          /* fmt chunk size   */
  put_u16 (&hdr[20], 1u);           /* PCM              */
  put_u16 (&hdr[22], 1u);           /* mono             */
  put_u32 (&hdr[24], SAMPLE_RATE);  /* sample rate      */
  put_u32 (&hdr[28], SAMPLE_RATE * 2u); /* byte rate    */
  put_u16 (&hdr[32], 2u);           /* block align      */
  put_u16 (&hdr[34], 16u);          /* bits per sample  */
  memcpy (&hdr[36], "data", 4);
  put_u32 (&hdr[40], data_size);

  f = fopen (path, "wb");
  if (!f)
    return -1;
  if (fwrite (hdr, 1, sizeof (hdr), f) != sizeof (hdr))
    {
      fclose (f);
      return -1;
    }
  for (i = 0; i < (uint32_t) FRAMES; i++)
    {
      double v =
        0.75 * sin (2.0 * 3.14159265358979323846 * FREQ *
                    ((double) i / (double) SAMPLE_RATE));
      int16_t s = (int16_t) (v * 32767.0);
      uint8_t b[2];
      put_u16 (b, (uint16_t) s);
      if (fwrite (b, 1, 2, f) != 2)
        {
          fclose (f);
          return -1;
        }
    }
  fclose (f);
  return 0;
}

int
main (int argc, const char * argv[])
{
  const char * path = (argc > 1) ? argv[1] : "audec_smoke.wav";
  AudecInfo nfo;
  AudecHandle * handle;
  float * out = NULL;
  ssize_t samples;
  float peak = 0.0f;
  size_t i;
  const size_t expected_resampled =
    (size_t) ((double) FRAMES * (24000.0 / (double) SAMPLE_RATE));

  if (write_wav (path) != 0)
    {
      printf ("FAIL: cannot synthesize WAV at %s\n", path);
      return 2;
    }

  audec_init ();

  /* 1-4: file info through the sndfile-backed probe */
  memset (&nfo, 0, sizeof (nfo));
  CHECK (audec_finfo (path, &nfo) == 0, "audec_finfo succeeds");
  CHECK ((size_t) nfo.frames == (size_t) FRAMES, "frames == 16000");
  CHECK (nfo.sample_rate == SAMPLE_RATE, "sample_rate == 48000");
  CHECK (nfo.channels == 1, "channels == 1");

  /* 5-8: decode pass-through (no resampling) */
  memset (&nfo, 0, sizeof (nfo));
  handle = audec_open (path, &nfo);
  CHECK (handle != NULL, "audec_open returns a handle");
  samples = audec_read (handle, &out, (int) SAMPLE_RATE);
  CHECK (samples == (ssize_t) FRAMES, "audec_read reads all 16000 frames");
  for (i = 0; out != NULL && i < (size_t) samples; i++)
    {
      float v = out[i];
      if (v > peak)
        peak = v;
      if (v < -peak)
        peak = -v;
    }
  CHECK (out != NULL && peak > 0.01f && peak <= 1.0f,
         "decoded peak amplitude in (0.01, 1.0]");
  CHECK (audec_close (handle) == 0, "audec_close succeeds");
  free (out);

  /* 9-12: decode with libsamplerate down-sample 48000 -> 24000 */
  memset (&nfo, 0, sizeof (nfo));
  handle = audec_open (path, &nfo);
  CHECK (handle != NULL, "audec_open (resample pass) returns a handle");
  out = NULL;
  samples = audec_read (handle, &out, 24000);
  CHECK (samples == (ssize_t) expected_resampled,
         "resampled read == 8000 frames (48000 -> 24000)");
  CHECK (out != NULL && samples > 0 &&
         isfinite ((double) out[0]) &&
         isfinite ((double) out[samples - 1]),
         "resampled samples are finite");
  CHECK (audec_close (handle) == 0, "audec_close (resample pass) succeeds");
  free (out);

  audec_free_nfo (&nfo);

  printf ("SUMMARY: %s (12 assertions, %d failure(s))\n",
          failures == 0 ? "PASS" : "FAIL", failures);
  return failures == 0 ? 0 : 1;
}
