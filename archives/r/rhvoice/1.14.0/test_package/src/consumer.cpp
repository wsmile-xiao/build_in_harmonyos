/* Consumer acceptance test for the packaged RHVoice engine.
 *
 * The engine is driven through its public C API only: the test locates the
 * installed configuration and data directories, builds an engine, walks the
 * voice table and synthesizes a short utterance, counting the audio the
 * callbacks receive.  A library that links but cannot produce a single sample
 * fails this test, which is the point of the exercise on a new platform.
 */

#include <cstdio>
#include <cstring>
#include <string>
#include <sys/stat.h>

#include "RHVoice.h"

namespace {

int failures = 0;

void check(bool condition, const char* message)
{
  if (condition)
    {
      printf("PASS: %s\n", message);
    }
  else
    {
      printf("FAIL: %s\n", message);
      ++failures;
    }
}

bool is_dir(const std::string& path)
{
  struct stat info;
  return stat(path.c_str(), &info) == 0 && S_ISDIR(info.st_mode);
}

bool is_file(const std::string& path)
{
  struct stat info;
  return stat(path.c_str(), &info) == 0 && S_ISREG(info.st_mode);
}

std::string join(const std::string& left, const std::string& right)
{
  return left + "/" + right;
}

std::string find_dir(const std::string& package_folder, const char* relative)
{
  std::string candidate = join(package_folder, relative);
  return is_dir(candidate) ? candidate : std::string();
}

/* RHVoice hands the synthesized audio to the callbacks attached to the message,
 * so the test collects what the engine actually produces. */
struct capture
{
  capture(): sample_rate(0), samples(0), finished(false)
  {
  }

  int sample_rate;
  unsigned long long samples;
  bool finished;
};

capture result;

int on_set_sample_rate(int sample_rate, void* user_data)
{
  if (user_data)
    static_cast<capture*>(user_data)->sample_rate = sample_rate;
  printf("  callback set_sample_rate: %d\n", sample_rate);
  return 1;
}

int on_play_speech(const short* samples, unsigned int count, void* user_data)
{
  (void) samples;
  if (user_data)
    static_cast<capture*>(user_data)->samples += count;
  return 1;
}

void on_done(void* user_data)
{
  if (user_data)
    static_cast<capture*>(user_data)->finished = true;
}

} // namespace

int main(int argc, char* argv[])
{
  printf("RHVoice consumer test\n");
  if (argc < 2)
    {
      printf("usage: rhvoice_consumer <package_folder>\n");
      return 2;
    }
  const std::string package_folder(argv[1]);
  printf("  library version: %s\n", RHVoice_get_version());

  /* The package installs RHVoice.conf below etc/RHVoice and the language/voice
   * data below share/RHVoice; both are looked up relative to the package. */
  std::string config_path;
  for (const char* relative : {"usr/etc/RHVoice", "etc/RHVoice"})
    {
      std::string candidate = find_dir(package_folder, relative);
      if (!candidate.empty() && is_file(join(candidate, "RHVoice.conf")))
        {
          config_path = candidate;
          break;
        }
    }
  std::string data_path;
  for (const char* relative : {"usr/share/RHVoice", "share/RHVoice"})
    {
      std::string candidate = find_dir(package_folder, relative);
      if (!candidate.empty() && is_dir(join(candidate, "languages")))
        {
          data_path = candidate;
          break;
        }
    }
  printf("  config_path: %s\n", config_path.empty() ? "(not installed)" : config_path.c_str());
  printf("  data_path:   %s\n", data_path.empty() ? "(no voice data installed)" : data_path.c_str());
  check(!config_path.empty(), "the installed configuration directory is present");
  check(!data_path.empty(), "the installed voice data directory is present");
  if (config_path.empty() || data_path.empty())
    {
      printf("%d checks failed\n", failures);
      return 1;
    }

  RHVoice_init_params params;
  memset(&params, 0, sizeof(params));
  params.config_path = config_path.c_str();
  params.data_path = data_path.c_str();
  params.callbacks.set_sample_rate = on_set_sample_rate;
  params.callbacks.play_speech = on_play_speech;
  params.callbacks.done = on_done;

  RHVoice_tts_engine engine = RHVoice_new_tts_engine(&params);
  check(engine != 0, "RHVoice_new_tts_engine() returns an engine");
  if (!engine)
    {
      printf("%d checks failed\n", failures);
      return 1;
    }

  const unsigned int voices = RHVoice_get_number_of_voices(engine);
  printf("  voices: %u\n", voices);
  check(voices > 0, "the engine exposes at least one voice");
  const RHVoice_voice_info* voice_table = RHVoice_get_voices(engine);
  check(voice_table != 0, "RHVoice_get_voices() returns a voice table");
  if (voices == 0 || !voice_table)
    {
      RHVoice_delete_tts_engine(engine);
      printf("%d checks failed\n", failures);
      return 1;
    }
  for (unsigned int i = 0; i < voices; ++i)
    printf("    voice %u: name=%s language=%s\n", i,
           voice_table[i].name ? voice_table[i].name : "?",
           voice_table[i].language ? voice_table[i].language : "?");
  check(voice_table[0].name != 0 && voice_table[0].name[0] != '\0',
        "the first voice reports a name");
  check(voice_table[0].language != 0 && voice_table[0].language[0] != '\0',
        "the first voice reports a language");

  /* Two identical languages share every letter, so they are not a valid
   * bilingual (voice profile) combination: the query must answer 0. */
  const int compatible = RHVoice_are_languages_compatible(engine, voice_table[0].language,
                                                          voice_table[0].language);
  printf("  are_languages_compatible(%s, %s) = %d\n", voice_table[0].language,
         voice_table[0].language, compatible);
  check(compatible == 0, "a language is not a bilingual combination with itself");

  const char* text = "Hello, HarmonyOS.";
  RHVoice_synth_params synth_params;
  memset(&synth_params, 0, sizeof(synth_params));
  synth_params.voice_profile = voice_table[0].name;
  synth_params.relative_rate = 1.0;
  synth_params.relative_pitch = 1.0;
  synth_params.relative_volume = 1.0;

  RHVoice_message message = RHVoice_new_message(engine, text,
                                                static_cast<unsigned int>(strlen(text)),
                                                RHVoice_message_text, &synth_params, &result);
  check(message != 0, "RHVoice_new_message() returns a message");
  if (message)
    {
      RHVoice_speak(message);
      RHVoice_delete_message(message);
    }
  printf("  synthesized %llu samples at %d Hz\n", result.samples, result.sample_rate);
  check(result.sample_rate > 0, "the engine reports the sample rate it synthesized at");
  check(result.samples > 0, "synthesis hands audio samples to the callbacks");
  check(result.finished, "the engine signals the end of the utterance");

  RHVoice_delete_tts_engine(engine);
  if (failures)
    printf("%d checks failed\n", failures);
  else
    printf("all checks passed\n");
  return failures ? 1 : 0;
}
