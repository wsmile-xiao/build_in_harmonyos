/* libfishsound 1.0.1 consumer test for OpenHarmony (aarch64).
 *
 * Exercises the public API the way upstream src/tests/encdec-audio.c does:
 * per-channel PCM buffers, fish_sound_prepare_truncation() before each
 * encode (the last block carries the EOS flag that makes the Vorbis codec
 * flush its final blocks), packets collected via the FishSoundEncoded
 * callback, identified with fish_sound_identify(), then fed to
 * fish_sound_decode() while counting decoded frames. Vorbis and Speex are
 * both round-tripped, so linking against the conan package and all codec
 * dependencies is verified at run time.
 *
 * Note: fish_sound_encode_float() documents "number of frames encoded",
 * but 1.0.1's non-interleaved Vorbis path (fs_vorbis_encode_f) always
 * returns 0; only errors (<0) are asserted here, matching upstream tests
 * which ignore the return value.
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <fishsound/fishsound.h>

#define ENC_BLOCKS 4
#define FRAME_BLOCK 256
#define MAX_PACKETS 512
#define MAX_BYTES (4u << 20)

/* upstream encdec-audio expects Speex output padded to 320-frame windows */
#define SPEEX_WINDOW 320

static int failures = 0;

/* printf-style CHECK so assertion sites stay one-line and countable */
#define CHECK(cond, ...)                          \
  do {                                            \
    if (!(cond)) {                                \
      printf ("%s:%d: FAIL: ", __FILE__, __LINE__); \
      printf (__VA_ARGS__);                       \
      printf ("\n");                              \
      failures++;                                 \
    }                                             \
  } while (0)

typedef struct {
  unsigned char data[MAX_BYTES];
  long offsets[MAX_PACKETS];
  long lengths[MAX_PACKETS];
  int count;
  int overflow;
} packet_sink;

static int
encoded (FishSound * fsound, unsigned char * buf, long bytes, void * user_data)
{
  packet_sink * sink = (packet_sink *) user_data;
  long start;

  if (sink->count >= MAX_PACKETS) {
    sink->overflow = 1;
    return 1;
  }

  start = (sink->count == 0) ? 0
      : sink->offsets[sink->count - 1] + sink->lengths[sink->count - 1];

  if (start + bytes > MAX_BYTES) {
    sink->overflow = 1;
    return 1;
  }

  memcpy (sink->data + start, buf, bytes);
  sink->offsets[sink->count] = start;
  sink->lengths[sink->count] = bytes;
  sink->count++;

  return 0;
}

static long decoded_frames;

static int
decoded (FishSound * fsound, float * pcm[], long frames, void * user_data)
{
  decoded_frames += frames;
  return 0;
}

/* Encode FRAME_BLOCK frames per block for ENC_BLOCKS blocks (marking the
 * last block as end-of-stream), then decode every collected packet.
 * Returns 0 on success. */
static int
roundtrip (int format, int samplerate, int channels, const char * name)
{
  FishSoundInfo fsinfo;
  FishSound * encoder, * decoder;
  packet_sink sink;
  float ** pcm;
  long i, j, enc_frames = 0, expected_out;
  int ok = 1;

  printf ("---- %s (rate=%d channels=%d) ...\n", name, samplerate, channels);

  memset (&sink, 0, sizeof (sink));
  decoded_frames = 0;

  fsinfo.format = format;
  fsinfo.samplerate = samplerate;
  fsinfo.channels = channels;

  encoder = fish_sound_new (FISH_SOUND_ENCODE, &fsinfo);
  CHECK (encoder != NULL, "fish_sound_new (encode) failed for %s", name);
  decoder = fish_sound_new (FISH_SOUND_DECODE, &fsinfo);
  CHECK (decoder != NULL, "fish_sound_new (decode) failed for %s", name);
  if (encoder == NULL || decoder == NULL) {
    if (encoder) fish_sound_delete (encoder);
    if (decoder) fish_sound_delete (decoder);
    return 1;
  }

  CHECK (fish_sound_set_encoded_callback (encoder, encoded, &sink) == 0,
         "fish_sound_set_encoded_callback failed for %s", name);
  CHECK (fish_sound_set_decoded_float (decoder, decoded, NULL) == 0,
         "fish_sound_set_decoded_float failed for %s", name);

  /* fish_sound_encode_float() takes float * pcm[]: one pointer per
   * channel (non-interleaved), exactly as upstream src/tests does */
  pcm = (float **) malloc (sizeof (float *) * channels);
  CHECK (pcm != NULL, "malloc failed");
  if (pcm == NULL) return 1;
  for (i = 0; i < channels; i++) {
    pcm[i] = (float *) malloc (sizeof (float) * FRAME_BLOCK);
    CHECK (pcm[i] != NULL, "malloc failed");
    if (pcm[i] == NULL) return 1;
    /* square wave: non-zero input, no test data files required */
    for (j = 0; j < FRAME_BLOCK; j++)
      pcm[i][j] = ((j % 100) < 50) ? 0.5f : -0.5f;
  }

  for (i = 0; i < ENC_BLOCKS; i++) {
    long r;
    fish_sound_prepare_truncation (encoder, (i + 1) * FRAME_BLOCK,
                                   i == (ENC_BLOCKS - 1));
    r = fish_sound_encode_float (encoder, pcm, FRAME_BLOCK);
    CHECK (r >= 0, "fish_sound_encode_float failed (%ld) for %s", r, name);
    enc_frames += FRAME_BLOCK;
  }

  CHECK (fish_sound_flush (encoder) == 0, "fish_sound_flush failed for %s",
         name);

  CHECK (!sink.overflow, "packet sink overflow for %s", name);
  CHECK (sink.count > 0, "no packets encoded for %s", name);

  if (sink.count > 0 && !sink.overflow) {
    CHECK (fish_sound_identify (sink.data, sink.lengths[0]) == format,
           "fish_sound_identify did not return %s on first packet", name);

    for (i = 0; i < sink.count; i++) {
      long r = fish_sound_decode (decoder, sink.data + sink.offsets[i],
                                  sink.lengths[i]);
      CHECK (r >= 0, "fish_sound_decode failed on packet %ld for %s", i,
             name);
    }
  }

  /* Vorbis with a prepared end-of-stream decodes exactly the submitted
   * frames; Speex pads the final 320-frame window (upstream formula) */
  expected_out = enc_frames;
  if (format == FISH_SOUND_SPEEX)
    expected_out += (SPEEX_WINDOW - (enc_frames % SPEEX_WINDOW));

  CHECK (decoded_frames == expected_out,
         "decoded frames %ld != expected %ld for %s", decoded_frames,
         expected_out, name);

  if (decoded_frames != expected_out || sink.overflow || sink.count == 0)
    ok = 0;

  fish_sound_delete (encoder);
  fish_sound_delete (decoder);
  for (i = 0; i < channels; i++) free (pcm[i]);
  free (pcm);

  if (ok)
    printf ("---- %s: encoded %ld frames in %d packets, decoded %ld frames\n",
            name, enc_frames, sink.count, decoded_frames);

  return ok ? 0 : 1;
}

int
main (void)
{
  int rc = 0;

  rc |= roundtrip (FISH_SOUND_VORBIS, 44100, 2, "Vorbis");
  rc |= roundtrip (FISH_SOUND_SPEEX, 8000, 1, "Speex");

  if (failures == 0 && rc == 0) {
    printf ("libfishsound consumer test: all checks passed\n");
    return 0;
  }

  printf ("libfishsound consumer test: %d check(s) failed\n", failures);
  return 1;
}
