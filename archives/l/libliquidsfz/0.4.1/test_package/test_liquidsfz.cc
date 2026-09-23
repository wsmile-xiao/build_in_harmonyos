// Consumer round-trip test for the liquidsfz OHOS package.
// Writes a minimal PCM16 WAV fixture by hand, references it from a generated
// SFZ file, renders a note through LiquidSFZ::Synth (static libliquidsfz.a,
// which links libsndfile transitively) and asserts the output signal is
// non-silent and bounded.
#include <cmath>
#include <cstdio>
#include <cstdint>
#include <cstring>
#include <filesystem>
#include <fstream>
#include <string>
#include <vector>

#include <unistd.h>
#include <liquidsfz.hh>

#ifndef M_PI
#define M_PI 3.14159265358979323846
#endif

namespace fs = std::filesystem;

static const uint32_t kSampleRate = 48000;
static const uint32_t kToneSamples = kSampleRate; // 1 second

static void
put_u32 (std::string& out, uint32_t v)
{
  out.append (reinterpret_cast<const char*> (&v), 4);
}

static void
put_u16 (std::string& out, uint16_t v)
{
  out.append (reinterpret_cast<const char*> (&v), 2);
}

static bool
write_sine_wav (const std::string& path)
{
  std::string data;
  data.reserve (44 + kToneSamples * 2);
  for (uint32_t i = 0; i < kToneSamples; i++)
    {
      float s = 0.8f * sin (2.0f * M_PI * 440.0f * i / kSampleRate);
      int16_t v = static_cast<int16_t> (s * 32767.0f);
      put_u16 (data, static_cast<uint16_t> (v));
    }

  std::string wav;
  wav += "RIFF";
  put_u32 (wav, 36 + static_cast<uint32_t> (data.size()));
  wav += "WAVE";
  wav += "fmt ";
  put_u32 (wav, 16);          // fmt chunk size
  put_u16 (wav, 1);           // PCM
  put_u16 (wav, 1);           // mono
  put_u32 (wav, kSampleRate);
  put_u32 (wav, kSampleRate * 2); // byte rate
  put_u16 (wav, 2);           // block align
  put_u16 (wav, 16);          // bits per sample
  wav += "data";
  put_u32 (wav, static_cast<uint32_t> (data.size()));
  wav += data;

  std::ofstream out (path, std::ios::binary);
  out.write (wav.data(), wav.size());
  out.close();
  if (!out)
    {
      std::printf ("FAIL: cannot write %s\n", path.c_str());
      return false;
    }
  return true;
}

int
main (int argc, char **argv)
{
  fs::path workdir = (argc > 1) ? fs::path (argv[1]) : fs::path (".");
  std::error_code ec;
  fs::path scratch = workdir / ("liquidsfz_test_" + std::to_string (getpid()));
  fs::create_directory (scratch, ec);
  if (ec)
    {
      std::printf ("FAIL: cannot create scratch dir in %s: %s\n",
                   workdir.string().c_str(), ec.message().c_str());
      return 1;
    }

  int result = 1;
  std::string wav = (scratch / "sine440.wav").string();
  std::string sfz = (scratch / "test.sfz").string();

  if (!write_sine_wav (wav))
    goto cleanup;

  {
    std::ofstream out (sfz);
    out << "<region> sample=" << wav << " key=60 lovel=0 hivel=127\n";
    out.close();
    if (!out)
      {
        std::printf ("FAIL: cannot write %s\n", sfz.c_str());
        goto cleanup;
      }
  }

  {
    LiquidSFZ::Synth synth;
    synth.set_sample_rate (kSampleRate);

    if (synth.sample_rate() != kSampleRate)
      {
        std::printf ("FAIL: sample_rate() = %u\n", synth.sample_rate());
        goto cleanup;
      }

    if (!synth.load (sfz))
      {
        std::printf ("FAIL: synth.load(%s) returned false\n", sfz.c_str());
        goto cleanup;
      }

    // render one second of MIDI note 60
    synth.add_event_note_on (0, 0, 60, 100);

    const uint32_t block = 1024;
    std::vector<float> left (block), right (block);
    float *outputs[2] = { left.data(), right.data() };

    double peak = 0.0;
    const uint32_t blocks = kSampleRate / block;
    for (uint32_t b = 0; b < blocks; b++)
      {
        synth.process (outputs, block);
        for (uint32_t i = 0; i < block; i++)
          {
            peak = std::max (peak, (double) fabs (left[i]));
            peak = std::max (peak, (double) fabs (right[i]));
            if (!(fabs (left[i]) <= 1.0) || !(fabs (right[i]) <= 1.0))
              {
                std::printf ("FAIL: output out of range: %f/%f\n", left[i], right[i]);
                goto cleanup;
              }
          }
      }

    std::printf ("liquidsfz render peak amplitude: %.6f\n", peak);
    if (peak < 0.01)
      {
        std::printf ("FAIL: render is (almost) silent, peak=%f\n", peak);
        goto cleanup;
      }
    result = 0;
  }

cleanup:
  for (const auto& entry : fs::directory_iterator (scratch))
    fs::remove (entry.path());
  fs::remove (scratch);
  if (result == 0)
    std::printf ("PASS: liquidsfz render round-trip\n");
  return result;
}
