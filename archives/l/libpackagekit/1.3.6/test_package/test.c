/* test_package for libpackagekit 1.3.6
 *
 * Real consumer test (R34): links against libpackagekit-glib2 and exercises
 * its public API. We create a PkControl object (pk_control_new) and check the
 * version macros from the installed pk-version.h — this proves the library
 * compiles, links and that its headers/types are usable at runtime.
 */
#include <glib.h>
#include <packagekit-glib2/packagekit.h>
#include <stdio.h>

int main(void)
{
    g_autoptr(PkControl) control = NULL;

    /* version macros from the installed headers */
    g_assert_cmpint(PK_MAJOR_VERSION, ==, 1);
    g_assert_cmpint(PK_MINOR_VERSION, ==, 3);
    g_assert_cmpint(PK_MICRO_VERSION, ==, 6);

    /* instantiate a real object from the shared library */
    control = pk_control_new();
    g_assert(control != NULL);

    /* the object must be of the expected GObject type */
    g_assert_true(PK_IS_CONTROL(control));

    g_print("libpackagekit test OK: PkControl instantiated, version %d.%d.%d\n",
            PK_MAJOR_VERSION, PK_MINOR_VERSION, PK_MICRO_VERSION);
    return 0;
}
