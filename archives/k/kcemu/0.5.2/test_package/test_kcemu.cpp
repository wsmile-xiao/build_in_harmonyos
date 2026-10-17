/* Consumer test for the installed kcemu core libraries.
 *
 * Uses the installed kc/prefs + libdbg + sys headers and the packaged static
 * libraries (libprefs.a, libdbg.a, libsys_unix.a) to drive the preferences
 * layer - the same surface upstream's t_prefs test covers, but as an external
 * consumer of the installed package. */
#include <cstdio>
#include <cstdlib>
#include <string>

#include "sys/sysdep.h"
#include "kc/prefs/prefs.h"
#include "libdbg/dbg.h"

static int checks = 0;
static int fails = 0;

#define CHECK(cond, msg) do { \
    checks++; \
    if (!(cond)) { fails++; std::fprintf(stderr, "FAIL: %s\n", (msg)); } \
} while (0)

int main()
{
    DBGI()->add_path("KCemu/Preferences", true);

    const char *basedir = std::getenv("KCEMU_TEST_BASEDIR");
    std::string base = (basedir && basedir[0]) ? basedir : "kcemu-consumer";
    Preferences::init((base + "/sys").c_str(),
                      (base + "/config").c_str(),
                      (base + "/profiles").c_str());

    Preferences *prefs = Preferences::instance();
    CHECK(prefs != NULL, "Preferences::instance()");
    if (!prefs)
        return 1;

    CHECK(prefs->mkdirs(base + "/config"), "mkdirs creates the config dir");

    prefs->set_current_profile("kc85-4", 0);
    Profile *p = prefs->find_profile("kc85-4");
    CHECK(p != NULL, "find_profile(\"kc85-4\")");

    if (p)
        p->set_int_value("consumer_test", 42);

    prefs->save();
    CHECK(!prefs->has_changed_profiles(), "save clears the changed flags");

    std::printf("KCEMU_CHECK_SUMMARY checks=%d fails=%d\n", checks, fails);
    return fails == 0 ? 0 : 1;
}
