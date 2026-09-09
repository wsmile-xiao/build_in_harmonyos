/* test_package consumer test for libmirage (no image files required).
 *
 * Real functional coverage of the static libmirage.a:
 *   1. object construction through the GType system (proves the linked
 *      glib/gobject archives and libmirage's own registration resolve);
 *   2. mirage_mirage_get_version() round-trip: the core API returns the
 *      library version string ("1.0.0") through its GError-based contract.
 */
#include <mirage.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(cond) do { if (!(cond)) { \
    fprintf (stderr, "FAILED: %s (line %d)\n", #cond, __LINE__); \
    exit (1); } } while (0)

int
main (void)
{
  MIRAGE_Mirage *mirage;
  GError *error = NULL;
  gchar *version = NULL;

  /* 1. construct the top-level context object */
  mirage = g_object_new (MIRAGE_TYPE_MIRAGE, NULL);
  CHECK (mirage != NULL);
  CHECK (MIRAGE_IS_MIRAGE (mirage));

  /* 2. real API call: version query through the library's GError contract */
  CHECK (mirage_mirage_get_version (mirage, &version, &error));
  CHECK (error == NULL);
  CHECK (version != NULL);
  CHECK (strcmp (version, "1.0.0") == 0);

  g_free (version);
  g_object_unref (mirage);

  printf ("libmirage test_package: all checks passed\n");
  return 0;
}
