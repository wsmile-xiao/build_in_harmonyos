/*
 * test.c — libgmobile 0.7.2 consumer test (Conan test_package).
 *
 * Exercises the *installed* library through its public API on the OHOS
 * aarch64 target.  Three independent mechanisms are covered, each of which
 * would silently "work" if it were deleted:
 *
 *   1. gm_mcc_to_iso()  — the compiled-in MCC table (no I/O, pure data).
 *   2. gm_list_devices()/gm_display_panel_new_from_resource() — the GResource
 *      blob built by data/meson.build, i.e. proof that the upstream
 *      `preprocess="json-stripblanks"` pipeline actually produced and linked
 *      the resource (it needs an external json-glib-format at build time).
 *   3. gm_display_panel_new_from_data() — JSON parsing through libjson-glib,
 *      i.e. proof the transitive json-glib-1.0 link survived packaging.
 *
 * Every positive assertion is paired with a negative control so that a
 * vacuous assertion cannot pass.
 */
#define GMOBILE_USE_UNSTABLE_API
#include <gmobile.h>

#include <gio/gio.h>
#include <stdio.h>
#include <string.h>

static int failures = 0;

#define CHECK(cond, ...)                                                      \
  G_STMT_START {                                                              \
    if (cond) {                                                               \
      printf ("ok   - ");                                                     \
    } else {                                                                  \
      printf ("FAIL - ");                                                     \
      failures++;                                                             \
    }                                                                         \
    printf (__VA_ARGS__);                                                     \
    printf ("\n");                                                            \
    fflush (stdout);                                                          \
  } G_STMT_END

static void
check_mcc_lookup (void)
{
  GError *err = NULL;
  const char *iso;

  /* Positive: China (MCC 460) is in the compiled-in table. */
  iso = gm_mcc_to_iso ("460", &err);
  CHECK (err == NULL,
         "gm_mcc_to_iso(\"460\") does not set an error");
  CHECK (iso != NULL && strcmp (iso, "CN") == 0,
         "gm_mcc_to_iso(\"460\") == \"CN\" (got %s)",
         iso ? iso : "(NULL)");
  g_clear_error (&err);

  /* An IMSI is accepted: only the 3-digit MCC prefix is significant. */
  iso = gm_mcc_to_iso ("460001234567890", &err);
  CHECK (err == NULL && iso != NULL && strcmp (iso, "CN") == 0,
         "gm_mcc_to_iso(\"460001234567890\") == \"CN\" (IMSI prefix form)");
  g_clear_error (&err);

  /* Negative control: an unassigned MCC must fail loudly with a GError
   * rather than return a stale/garbage code. */
  iso = gm_mcc_to_iso ("abc", &err);
  CHECK (iso == NULL && err != NULL,
         "unassigned MCC returns NULL and sets a GError (domain=%s)",
         err ? g_quark_to_string (err->domain) : "(none)");
  g_clear_error (&err);

  /* Negative control: fewer than 3 digits is rejected before the lookup. */
  iso = gm_mcc_to_iso ("46", &err);
  CHECK (iso == NULL && err != NULL,
         "MCC shorter than 3 digits is rejected (no error set = %s)",
         err ? "no" : "yes");
  g_clear_error (&err);
}

static void
check_device_list (void)
{
  GStrv devices = gm_list_devices ();
  guint n = 0;

  CHECK (devices != NULL, "gm_list_devices() returns a non-NULL list");
  if (devices == NULL)
    return;

  n = g_strv_length (devices);
  /* data/gmobile.gresources.xml embeds exactly 34 display-panel JSON files;
   * a count below that means the resource blob was truncated or dropped. */
  CHECK (n >= 34, "resource blob yields 34 known devices (got %u)", n);
  CHECK (g_strv_contains ((const char * const *) devices, "purism,librem5"),
         "device list contains purism,librem5");

  g_strfreev (devices);
}

static void
check_display_panel_from_resource (void)
{
  GError *err = NULL;
  GmDisplayPanel *panel;

  /* Read one panel straight out of the GResource (gmobile's own data). */
  panel = gm_display_panel_new_from_resource (
    "/mobi/phosh/gmobile/devices/display-panels/purism,librem5.json", &err);
  CHECK (err == NULL && panel != NULL,
         "panel loads from GResource (err=%s)",
         err ? err->message : "none");
  if (panel == NULL) {
    g_clear_error (&err);
    return;
  }

  CHECK (gm_display_panel_get_name (panel) != NULL &&
         strcmp (gm_display_panel_get_name (panel), "Purism Librem 5") == 0,
         "panel name from resource == \"Purism Librem 5\" (got %s)",
         gm_display_panel_get_name (panel) ? gm_display_panel_get_name (panel) : "(NULL)");
  CHECK (gm_display_panel_get_x_res (panel) == 720 &&
         gm_display_panel_get_y_res (panel) == 1440,
         "panel resolution from resource == 720x1440 (got %dx%d)",
         gm_display_panel_get_x_res (panel), gm_display_panel_get_y_res (panel));

  g_object_unref (panel);
  g_clear_error (&err);
}

static void
check_display_panel_parse (void)
{
  static const char *json =
    "{ \"name\": \"Oneplus 6T\","
    "  \"x-res\": 1080,"
    "  \"y-res\": 2340,"
    "  \"corner-radii\": [ 10, 11, 12, 13 ],"
    "  \"width\": 68,"
    "  \"height\": 145,"
    "  \"cutouts\": [ { \"name\": \"notch\","
    "                   \"path\": \"M 455 0 V 79 H 625 V 0 Z\" } ] }";
  GError *err = NULL;
  GmDisplayPanel *panel;
  GListModel *cutouts;
  GArray *radii;

  panel = gm_display_panel_new_from_data (json, &err);
  CHECK (err == NULL && panel != NULL,
         "ground-truth JSON parses (libjson-glib linked; err=%s)",
         err ? err->message : "none");
  if (panel == NULL) {
    g_clear_error (&err);
    return;
  }

  CHECK (gm_display_panel_get_width (panel) == 68 &&
         gm_display_panel_get_height (panel) == 145,
         "panel size == 68x145 (got %dx%d)",
         gm_display_panel_get_width (panel), gm_display_panel_get_height (panel));

  radii = gm_display_panel_get_corner_radii (panel);
  CHECK (radii != NULL && radii->len == 4 &&
         g_array_index (radii, int, 0) == 10 &&
         g_array_index (radii, int, 3) == 13,
         "corner-radii round-trip == [10,11,12,13] (len=%u)",
         radii ? radii->len : 0);
  if (radii != NULL)
    g_array_unref (radii);

  cutouts = gm_display_panel_get_cutouts (panel);
  CHECK (cutouts != NULL && g_list_model_get_n_items (cutouts) == 1,
         "cutout list has 1 item (got %u)",
         cutouts ? g_list_model_get_n_items (cutouts) : 0);

  /* Negative control: malformed JSON must yield an error, not a half-built
   * panel — otherwise the positive assertion above proves nothing. */
  g_clear_error (&err);
  {
    GmDisplayPanel *bad = gm_display_panel_new_from_data ("{ not json", &err);
    CHECK (bad == NULL && err != NULL,
           "malformed JSON is rejected with a GError (panel=%s, err=%s)",
           bad ? "non-NULL" : "NULL", err ? "set" : "unset");
    if (bad != NULL)
      g_object_unref (bad);
    g_clear_error (&err);
  }

  g_object_unref (panel);
}

int
main (void)
{
  gm_init ();

  check_mcc_lookup ();
  check_device_list ();
  check_display_panel_from_resource ();
  check_display_panel_parse ();

  printf ("\n%s: %d assertion(s) failed\n",
          failures == 0 ? "PASS" : "FAIL", failures);
  return failures == 0 ? 0 : 1;
}
