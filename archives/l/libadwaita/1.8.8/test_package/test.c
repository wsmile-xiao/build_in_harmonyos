/* test.c — libadwaita 1.8.8 consumer test (Conan L1, R34) + no-display
 * functional probes.
 *
 * OHOS has no display server (GTK4 Broadway-only backend; broadwayd is
 * unrunnable under the signature constraint), so adw_init()/gtk_init()
 * cannot be executed here. This test deliberately does NOT call adw_init()
 * and exercises only the display-free subset of the public libadwaita-1
 * API (E471 methodology — the "no-display API probes" approach extended
 * from the gtkmm 4.0.0.1 C++ bindings to this C-native GNOME UI library).
 *
 * Ported upstream assertions (1:1, assertion-for-assertion, public API):
 *   B. tests/test-easing.c — all 35 AdwEasing values, 2 assertions each
 *      (f(0)~=0, f(1)~=1, eps 0.005 = upstream
 *      g_assert_cmpfloat_with_epsilon contract) => 70 assertions
 *   C. tests/test-accent-color.c — public-API assertions:
 *      to_rgba (9) + to_standalone_rgba (18) + rgba_to_standalone (8)
 *      => 35 assertions
 *
 * NOT portable (documented, with evidence — see notes.md):
 *   The remaining 137 assertions of test-accent-color.c
 *   (nearest_from_rgba roundtrip 10 + color palettes 127) call
 *   adw_accent_color_nearest_from_rgba(), which is declared ONLY in
 *   src/adw-accent-color-private.h (not in the installed public headers)
 *   and is NOT exported by libadwaita-1.so (verified: nm -D shows no
 *   such dynamic symbol). Upstream's own test binary links the internal
 *   static lib (libadwaita-1-internal.a, all symbols present); a
 *   consumer of the installed package cannot reach that symbol.
 *
 * Both upstream tests are pure-computation (no widget/display needed);
 * the port runs the identical public-API assertions in a no-display
 * context.
 *
 * Extended consumer assertions (beyond upstream):
 *   A. version / init-state (7)
 *   B. easing analytic midpoints + monotonicity (7, upstream only checks
 *      endpoints)
 *   D. spring physics params (5; upstream 1.8.8 has no test-spring-params;
 *      AdwSpringParams is a GBoxed, released via adw_spring_params_unref)
 *
 * Total: 124 checks, of which 105 are 1:1 upstream assertions
 * (70 + 35). Each failed check exits non-zero (R34 substantive
 * verification). Widget APIs (every type requiring gtk_init) and
 * adw_init itself are display-dependent and are NOT probed here — see
 * notes.md for the full API display-dependency classification table and
 * empirical results.
 */
#include <adwaita.h>

#include <glib.h> /* g_snprintf（显式声明来源，不依赖 adwaita.h 间接引入） */
#include <math.h> /* round, fabs */
#include <stdio.h>

static int g_checks = 0;

static int check(int condition, const char *what)
{
  g_checks++;
  if (!condition)
    fprintf(stderr, "FAIL: %s\n", what);
  return condition;
}

static int near(double a, double b)
{
  return fabs(a - b) < 1e-6;
}

/* ── helpers ported from tests/test-accent-color.c (upstream) ────────── */
static int rgba_to_hex(GdkRGBA *rgba)
{
  return (int) (round (rgba->red   * 0xff)) << 16 |
         (int) (round (rgba->green * 0xff)) << 8 |
         (int) (round (rgba->blue  * 0xff));
}

static void hex_to_rgba(int hex, GdkRGBA *rgba)
{
  rgba->red   = (float) ((hex >> 16) & 0xff) / 0xff;
  rgba->green = (float) ((hex >> 8)  & 0xff) / 0xff;
  rgba->blue  = (float) ((hex)       & 0xff) / 0xff;
  rgba->alpha = 1;
}

static int hex_of(AdwAccentColor c)
{
  GdkRGBA rgba;
  adw_accent_color_to_rgba(c, &rgba);
  return rgba_to_hex(&rgba);
}

static int hex_of_standalone(AdwAccentColor c, gboolean dark)
{
  GdkRGBA rgba;
  adw_accent_color_to_standalone_rgba(c, dark, &rgba);
  return rgba_to_hex(&rgba);
}

static int rgba_standalone_hex(int in, gboolean dark)
{
  GdkRGBA rgba;
  hex_to_rgba(in, &rgba);
  adw_rgba_to_standalone(&rgba, dark, &rgba);
  return rgba_to_hex(&rgba);
}

int main(void)
{
  int ok = 1;

  /* ── A. version / init-state (extended consumer assertions) ───────── */
  ok &= check(adw_get_major_version() == 1, "adw_get_major_version() == 1");
  ok &= check(adw_get_minor_version() == 8, "adw_get_minor_version() == 8");
  ok &= check(adw_get_micro_version() == 8, "adw_get_micro_version() == 8");
  ok &= check(ADW_MAJOR_VERSION == 1 && ADW_MINOR_VERSION == 8 &&
              ADW_MICRO_VERSION == 8,
              "ADW_MAJOR/MINOR/MICRO_VERSION macros");
  ok &= check(ADW_CHECK_VERSION(1, 8, 8), "ADW_CHECK_VERSION(1,8,8)");
  ok &= check(!ADW_CHECK_VERSION(2, 0, 0), "!ADW_CHECK_VERSION(2,0,0)");
  ok &= check(!adw_is_initialized(), "adw_is_initialized() == FALSE (pre-init)");

  /* ── B. easing math ───────────────────────────────────────────────── */
  {
    /* Ported 1:1 from tests/test-easing.c: one test function per enum
     * value, each asserting
     *   g_assert_cmpfloat_with_epsilon (adw_easing_ease (easing, 0), 0, 0.005)
     *   g_assert_cmpfloat_with_epsilon (adw_easing_ease (easing, 1), 1, 0.005)
     * (35 values => 70 assertions). The eps 0.005 is the upstream
     * contract: the elastic family's analytic endpoints deviate from the
     * exact 0/1 by up to ~5e-4 (e.g. ease_in_elastic(0) = -4.88e-4,
     * ease_in_out_elastic(0) = 8.48e-5), so a strict check would reject
     * a conforming library.
     * (The upstream loop iterates g_type_class_ref(ADW_TYPE_EASING)
     * n_values; the enum is stable and contiguous, so an integer range
     * over ADW_LINEAR..ADW_EASE_IN_OUT covers exactly the same 35 values.) */
    int i;
    for (i = ADW_LINEAR; i <= ADW_EASE_IN_OUT; i++)
      {
        AdwEasing e = (AdwEasing) i;
        char label[64];
        g_snprintf(label, sizeof label, "easing[%d]: f(0)~=0 (eps 0.005)", i);
        ok &= check(fabs(adw_easing_ease(e, 0.0)) <= 0.005, label);
        g_snprintf(label, sizeof label, "easing[%d]: f(1)~=1 (eps 0.005)", i);
        ok &= check(fabs(adw_easing_ease(e, 1.0) - 1.0) <= 0.005, label);
      }
    /* Extended (beyond upstream, which only checks endpoints): */
    ok &= check(near(adw_easing_ease(ADW_LINEAR, 0.5), 0.5),
                "LINEAR(0.5) == 0.5");
    ok &= check(near(adw_easing_ease(ADW_EASE_IN_QUAD, 0.5), 0.25),
                "EASE_IN_QUAD(0.5) == 0.25");
    ok &= check(near(adw_easing_ease(ADW_EASE_OUT_QUAD, 0.5), 0.75),
                "EASE_OUT_QUAD(0.5) == 0.75");
    ok &= check(near(adw_easing_ease(ADW_EASE_IN_CUBIC, 0.5), 0.125),
                "EASE_IN_CUBIC(0.5) == 0.125");
    ok &= check(near(adw_easing_ease(ADW_EASE_OUT_CUBIC, 0.5), 0.875),
                "EASE_OUT_CUBIC(0.5) == 0.875");
    ok &= check(near(adw_easing_ease(ADW_EASE_IN_OUT_QUAD, 0.5), 0.5),
                "EASE_IN_OUT_QUAD(0.5) == 0.5");
    ok &= check(adw_easing_ease(ADW_EASE_IN, 0.25) <
                    adw_easing_ease(ADW_EASE_IN, 0.5) &&
                adw_easing_ease(ADW_EASE_IN, 0.5) <
                adw_easing_ease(ADW_EASE_IN, 0.75),
                "EASE_IN strictly increasing on (0,1)");
  }

  /* ── C. accent-color (1:1 port of the public-API assertions of
   *     tests/test-accent-color.c, 35) ─────────────────────────────── */
  {
    /* test_adw_accent_color_to_rgba (9 assertions, upstream lines 217-225). */
    ok &= check(hex_of(ADW_ACCENT_COLOR_BLUE)   == 0x3584e4, "to_rgba(BLUE)   == 0x3584e4");
    ok &= check(hex_of(ADW_ACCENT_COLOR_TEAL)   == 0x2190a4, "to_rgba(TEAL)   == 0x2190a4");
    ok &= check(hex_of(ADW_ACCENT_COLOR_GREEN)  == 0x3a944a, "to_rgba(GREEN)  == 0x3a944a");
    ok &= check(hex_of(ADW_ACCENT_COLOR_YELLOW) == 0xc88800, "to_rgba(YELLOW) == 0xc88800");
    ok &= check(hex_of(ADW_ACCENT_COLOR_ORANGE) == 0xed5b00, "to_rgba(ORANGE) == 0xed5b00");
    ok &= check(hex_of(ADW_ACCENT_COLOR_RED)    == 0xe62d42, "to_rgba(RED)    == 0xe62d42");
    ok &= check(hex_of(ADW_ACCENT_COLOR_PINK)   == 0xd56199, "to_rgba(PINK)   == 0xd56199");
    ok &= check(hex_of(ADW_ACCENT_COLOR_PURPLE) == 0x9141ac, "to_rgba(PURPLE) == 0x9141ac");
    ok &= check(hex_of(ADW_ACCENT_COLOR_SLATE)  == 0x6f8396, "to_rgba(SLATE)  == 0x6f8396");

    /* test_adw_accent_color_to_standalone_rgba (18 assertions,
     * upstream lines 234-252). */
    ok &= check(hex_of_standalone(ADW_ACCENT_COLOR_BLUE,   FALSE) == 0x0461be, "standalone light BLUE");
    ok &= check(hex_of_standalone(ADW_ACCENT_COLOR_TEAL,   FALSE) == 0x007184, "standalone light TEAL");
    ok &= check(hex_of_standalone(ADW_ACCENT_COLOR_GREEN,  FALSE) == 0x15772e, "standalone light GREEN");
    ok &= check(hex_of_standalone(ADW_ACCENT_COLOR_YELLOW, FALSE) == 0x905300, "standalone light YELLOW");
    ok &= check(hex_of_standalone(ADW_ACCENT_COLOR_ORANGE, FALSE) == 0xb62200, "standalone light ORANGE");
    ok &= check(hex_of_standalone(ADW_ACCENT_COLOR_RED,    FALSE) == 0xc00023, "standalone light RED");
    ok &= check(hex_of_standalone(ADW_ACCENT_COLOR_PINK,   FALSE) == 0xa2326c, "standalone light PINK");
    ok &= check(hex_of_standalone(ADW_ACCENT_COLOR_PURPLE, FALSE) == 0x8939a4, "standalone light PURPLE");
    ok &= check(hex_of_standalone(ADW_ACCENT_COLOR_SLATE,  FALSE) == 0x526678, "standalone light SLATE");
    ok &= check(hex_of_standalone(ADW_ACCENT_COLOR_BLUE,   TRUE)  == 0x81d0ff, "standalone dark BLUE");
    ok &= check(hex_of_standalone(ADW_ACCENT_COLOR_TEAL,   TRUE)  == 0x7bdff4, "standalone dark TEAL");
    ok &= check(hex_of_standalone(ADW_ACCENT_COLOR_GREEN,  TRUE)  == 0x8de698, "standalone dark GREEN");
    ok &= check(hex_of_standalone(ADW_ACCENT_COLOR_YELLOW, TRUE)  == 0xffc057, "standalone dark YELLOW");
    ok &= check(hex_of_standalone(ADW_ACCENT_COLOR_ORANGE, TRUE)  == 0xff9c5b, "standalone dark ORANGE");
    ok &= check(hex_of_standalone(ADW_ACCENT_COLOR_RED,    TRUE)  == 0xff888c, "standalone dark RED");
    ok &= check(hex_of_standalone(ADW_ACCENT_COLOR_PINK,   TRUE)  == 0xffa0d8, "standalone dark PINK");
    ok &= check(hex_of_standalone(ADW_ACCENT_COLOR_PURPLE, TRUE)  == 0xfba7ff, "standalone dark PURPLE");
    ok &= check(hex_of_standalone(ADW_ACCENT_COLOR_SLATE,  TRUE)  == 0xbbd1e5, "standalone dark SLATE");

    /* test_adw_accent_color_rgba_to_standalone (8 assertions,
     * upstream lines 261-271). */
    ok &= check(rgba_standalone_hex(0x3584e4, FALSE) == 0x0461be, "rgba_to_standalone 0x3584e4 light");
    ok &= check(rgba_standalone_hex(0x3584e4, TRUE)  == 0x81d0ff, "rgba_to_standalone 0x3584e4 dark");
    ok &= check(rgba_standalone_hex(0xffffff, FALSE) == 0x636363, "rgba_to_standalone 0xffffff light");
    ok &= check(rgba_standalone_hex(0xffffff, TRUE)  == 0xffffff, "rgba_to_standalone 0xffffff dark");
    ok &= check(rgba_standalone_hex(0x000000, FALSE) == 0x000000, "rgba_to_standalone 0x000000 light");
    ok &= check(rgba_standalone_hex(0x000000, TRUE)  == 0xcecece, "rgba_to_standalone 0x000000 dark");
    ok &= check(rgba_standalone_hex(0x959595, FALSE) == 0x636363, "rgba_to_standalone 0x959595 light");
    ok &= check(rgba_standalone_hex(0x959595, TRUE)  == 0xcecece, "rgba_to_standalone 0x959595 dark");

    /* NOTE: the remaining 137 assertions of upstream
     * test-adw-accent-color (nearest_from_rgba roundtrip 10 + palettes
     * 127) are NOT exercised here: they call
     * adw_accent_color_nearest_from_rgba(), a private API (declared only
     * in src/adw-accent-color-private.h, absent from libadwaita-1.so's
     * exported symbols — verified with nm -D). See notes.md. */
  }

  /* ── D. spring physics params (extended; GBoxed: adw_spring_params_unref) ─ */
  {
    AdwSpringParams *sp = adw_spring_params_new(1.0, 1.0, 100.0);
    ok &= check(sp != NULL, "adw_spring_params_new(1.0, 1.0, 100.0)");
    if (sp != NULL)
      {
        ok &= check(near(adw_spring_params_get_damping_ratio(sp), 1.0),
                    "get_damping_ratio() == 1.0");
        ok &= check(near(adw_spring_params_get_mass(sp), 1.0),
                    "get_mass() == 1.0");
        ok &= check(near(adw_spring_params_get_stiffness(sp), 100.0),
                    "get_stiffness() == 100.0");
        ok &= check(near(adw_spring_params_get_damping(sp),
                         2.0 * 1.0 * sqrt(1.0 * 100.0)),
                    "get_damping() == 2*zeta*sqrt(m*k) == 20.0");
        /* AdwSpringParams is a GBoxed (G_DEFINE_BOXED_TYPE with
         * gatomicrefcount), NOT a GObject: g_object_unref() on it is
         * undefined behavior (observed SIGSEGV in g_object_run_dispose
         * when the mass field's double bit-pattern is read as the
         * object's weak-ref datalist pointer). */
        adw_spring_params_unref(sp);
      }
  }

  printf("libadwaita-1.8.8 no-display probe: checks=%d %s "
         "(105/105 upstream-ported assertions included)\n",
         g_checks, ok ? "PASS" : "FAIL");
  return ok ? 0 : 1;
}
