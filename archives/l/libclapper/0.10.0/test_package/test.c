/*
 * libclapper 0.10.0 L1 consumer test.
 *
 * Links against the packaged libclapper-0.0, initializes the library and
 * exercises the public playback-library API without requiring any GStreamer
 * plugins (playbin etc. are not registered on a headless OHOS device):
 *
 *   - version helpers      (clapper_get_*_version / clapper_get_version_s)
 *   - library init         (clapper_init_check)
 *   - object construction  (clapper_marker_new + getters)
 */
#include <clapper/clapper.h>

#include <stdio.h>
#include <string.h>

static int g_pass = 0;
static int g_fail = 0;

#define CHECK(cond, name)                                                    \
  do {                                                                        \
    if ((cond)) {                                                            \
      g_pass++;                                                              \
      printf("[ok] %s\n", (name));                                           \
    } else {                                                                 \
      g_fail++;                                                              \
      printf("[FAIL] %s\n", (name));                                         \
    }                                                                        \
  } while (0)

int
main (int argc, char **argv)
{
  gint gi_argc = 1;
  gchar *gi_argv[] = { "test_clapper", NULL };
  gchar **gi_argv_ptr = gi_argv;
  ClapperMarker *marker;
  const gchar *version_s;

  printf ("libclapper test: linking libclapper-0.0\n");

  /* ---------- library init ---------- */
  CHECK (clapper_init_check (&gi_argc, &gi_argv_ptr) == TRUE,
         "clapper_init_check returns TRUE");

  /* ---------- version helpers ---------- */
  CHECK (clapper_get_major_version () == 0, "clapper_get_major_version == 0");
  CHECK (clapper_get_minor_version () == 10, "clapper_get_minor_version == 10");
  CHECK (clapper_get_micro_version () == 0, "clapper_get_micro_version == 0");
  version_s = clapper_get_version_s ();
  CHECK (version_s != NULL && strcmp (version_s, "0.10.0") == 0,
         "clapper_get_version_s == \"0.10.0\"");

  /* ---------- object construction / introspection ---------- */
  marker = clapper_marker_new (CLAPPER_MARKER_TYPE_CHAPTER,
                               "Chapter 1", 0.0, 10.0);
  CHECK (marker != NULL, "clapper_marker_new returns non-NULL");
  if (marker != NULL)
    {
      CHECK (CLAPPER_IS_MARKER (marker), "marker is a ClapperMarker");
      CHECK (clapper_marker_get_marker_type (marker) == CLAPPER_MARKER_TYPE_CHAPTER,
             "marker type == CLAPPER_MARKER_TYPE_CHAPTER");
      CHECK (clapper_marker_get_start (marker) == 0.0,
             "marker start == 0.0");
      CHECK (clapper_marker_get_end (marker) == 10.0,
             "marker end == 10.0");
      CHECK (clapper_marker_get_title (marker) != NULL &&
             strcmp (clapper_marker_get_title (marker), "Chapter 1") == 0,
             "marker title == \"Chapter 1\"");
      g_object_unref (marker);
    }

  /* ---------- summary ---------- */
  printf ("libclapper test: %d passed, %d failed\n", g_pass, g_fail);
  return g_fail == 0 ? 0 : 1;
}
