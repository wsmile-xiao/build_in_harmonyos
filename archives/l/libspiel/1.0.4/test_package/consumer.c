#include <spiel.h>

static SpielVoice *
new_voice (const char *name, const char *identifier)
{
  const char *languages[] = { "en-US", "en", NULL };
  return g_object_new (SPIEL_TYPE_VOICE, "name", name,
                       "identifier", identifier, "languages", languages, NULL);
}

static void
test_version (void)
{
  g_assert_cmpstr (SPIEL_VERSION_S, ==, "1.0.4");
  g_assert_true (SPIEL_CHECK_VERSION (1, 0, 4));
  g_assert_false (SPIEL_CHECK_VERSION (1, 0, 5));
}

static void
test_utterance_text (void)
{
  g_autoptr (SpielUtterance) utterance = spiel_utterance_new ("hello");
  g_assert_cmpstr (spiel_utterance_get_text (utterance), ==, "hello");
  spiel_utterance_set_text (utterance, "hello HarmonyOS");
  g_assert_cmpstr (spiel_utterance_get_text (utterance), ==, "hello HarmonyOS");
}

static void
test_utterance_language (void)
{
  g_autoptr (SpielUtterance) utterance = spiel_utterance_new ("test");
  g_assert_null (spiel_utterance_get_language (utterance));
  spiel_utterance_set_language (utterance, "zh-CN");
  g_assert_cmpstr (spiel_utterance_get_language (utterance), ==, "zh-CN");
}

static void
test_utterance_defaults (void)
{
  g_autoptr (SpielUtterance) utterance = spiel_utterance_new (NULL);
  g_assert_null (spiel_utterance_get_text (utterance));
  g_assert_cmpfloat (spiel_utterance_get_pitch (utterance), ==, 1.0);
  g_assert_cmpfloat (spiel_utterance_get_rate (utterance), ==, 1.0);
  g_assert_cmpfloat (spiel_utterance_get_volume (utterance), ==, 1.0);
}

static void
test_utterance_numeric (void)
{
  g_autoptr (SpielUtterance) utterance = spiel_utterance_new ("test");
  spiel_utterance_set_pitch (utterance, 1.5);
  spiel_utterance_set_rate (utterance, 0.5);
  spiel_utterance_set_volume (utterance, 0.25);
  g_assert_cmpfloat (spiel_utterance_get_pitch (utterance), ==, 1.5);
  g_assert_cmpfloat (spiel_utterance_get_rate (utterance), ==, 0.5);
  g_assert_cmpfloat (spiel_utterance_get_volume (utterance), ==, 0.25);
}

static void
test_utterance_ssml (void)
{
  g_autoptr (SpielUtterance) utterance = spiel_utterance_new ("<speak>hi</speak>");
  g_assert_false (spiel_utterance_get_is_ssml (utterance));
  spiel_utterance_set_is_ssml (utterance, TRUE);
  g_assert_true (spiel_utterance_get_is_ssml (utterance));
}

static void
test_voice_metadata (void)
{
  g_autoptr (SpielVoice) voice = new_voice ("English", "en-us");
  const char *const *languages = spiel_voice_get_languages (voice);
  g_assert_cmpstr (spiel_voice_get_name (voice), ==, "English");
  g_assert_cmpstr (spiel_voice_get_identifier (voice), ==, "en-us");
  g_assert_cmpstr (languages[0], ==, "en-US");
  g_assert_cmpstr (languages[1], ==, "en");
  g_assert_null (languages[2]);
}

static void
test_voice_format (void)
{
  g_autoptr (SpielVoice) voice = new_voice ("English", "en-us");
  g_assert_null (spiel_voice_get_output_format (voice));
  spiel_voice_set_output_format (voice, "audio/x-raw");
  g_assert_cmpstr (spiel_voice_get_output_format (voice), ==, "audio/x-raw");
}

static void
test_voice_identity (void)
{
  g_autoptr (SpielVoice) first = new_voice ("English", "en-us");
  g_autoptr (SpielVoice) equivalent = new_voice ("English", "en-us");
  g_autoptr (SpielVoice) different = new_voice ("French", "fr-fr");
  g_assert_true (spiel_voice_equal (first, equivalent));
  g_assert_cmpuint (spiel_voice_hash (first), ==, spiel_voice_hash (equivalent));
  g_assert_cmpint (spiel_voice_compare (first, equivalent, NULL), ==, 0);
  g_assert_false (spiel_voice_equal (first, different));
}

static void
test_utterance_voice (void)
{
  g_autoptr (SpielUtterance) utterance = spiel_utterance_new ("test");
  g_autoptr (SpielVoice) voice = new_voice ("English", "en-us");
  g_assert_null (spiel_utterance_get_voice (utterance));
  spiel_utterance_set_voice (utterance, voice);
  g_assert_true (spiel_utterance_get_voice (utterance) == voice);
}

int
main (int argc, char **argv)
{
  g_test_init (&argc, &argv, NULL);
  g_test_add_func ("/spiel/version", test_version);
  g_test_add_func ("/spiel/utterance-text", test_utterance_text);
  g_test_add_func ("/spiel/utterance-language", test_utterance_language);
  g_test_add_func ("/spiel/utterance-defaults", test_utterance_defaults);
  g_test_add_func ("/spiel/utterance-numeric", test_utterance_numeric);
  g_test_add_func ("/spiel/utterance-ssml", test_utterance_ssml);
  g_test_add_func ("/spiel/voice-metadata", test_voice_metadata);
  g_test_add_func ("/spiel/voice-format", test_voice_format);
  g_test_add_func ("/spiel/voice-identity", test_voice_identity);
  g_test_add_func ("/spiel/utterance-voice", test_utterance_voice);
  return g_test_run ();
}
