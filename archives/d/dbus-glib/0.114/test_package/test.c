/* test_package consumer test for dbus-glib (no session bus required).
 *
 * Real functional coverage of the static libdbus-glib-1.a:
 *   1. specializable GType system: collection/map registration and
 *      specialization queries (the core dbus_g_type_* feature lives
 *      entirely in libdbus-glib);
 *   2. a typed collection round-trip through the append-context API
 *      (mirrors upstream test_as_ptrarray);
 *   3. DBUS_GERROR name extraction (error-mapping layer);
 *   4. transitively exercises the linked glib/dbus/expat archives.
 */
#include <dbus/dbus-glib.h>
#include <dbus/dbus-glib-lowlevel.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#define CHECK(cond) do { if (!(cond)) { \
    fprintf (stderr, "FAILED: %s (line %d)\n", #cond, __LINE__); \
    exit (1); } } while (0)

int
main (void)
{
  GType coll;
  GType map;
  GValue val = { 0, };
  GPtrArray *arr;
  DBusGTypeSpecializedAppendContext ctx;

  dbus_g_type_specialized_init ();

  /* 1. collection specialization registry */
  coll = dbus_g_type_get_collection ("GPtrArray", G_TYPE_STRING);
  CHECK (coll != G_TYPE_NONE);
  CHECK (dbus_g_type_is_collection (coll));
  CHECK (dbus_g_type_get_collection_specialization (coll) == G_TYPE_STRING);
  CHECK (!dbus_g_type_is_collection (G_TYPE_STRING));

  /* 2. map specialization registry */
  map = dbus_g_type_get_map ("GHashTable", G_TYPE_STRING, G_TYPE_STRING);
  CHECK (map != G_TYPE_NONE);
  CHECK (dbus_g_type_is_map (map));
  CHECK (dbus_g_type_get_map_key_specialization (map) == G_TYPE_STRING);
  CHECK (dbus_g_type_get_map_value_specialization (map) == G_TYPE_STRING);

  /* 3. full typed round-trip through the collection append API */
  arr = dbus_g_type_specialized_construct (coll);
  CHECK (arr != NULL);
  CHECK (arr->len == 0);
  g_value_init (&val, coll);
  g_value_take_boxed (&val, arr);
  dbus_g_type_specialized_init_append (&val, &ctx);
  {
    GValue elt = { 0, };
    g_value_init (&elt, G_TYPE_STRING);
    g_value_set_static_string (&elt, "consumer");
    dbus_g_type_specialized_collection_append (&ctx, &elt);
    g_value_unset (&elt);
  }
  dbus_g_type_specialized_collection_end_append (&ctx);
  arr = g_value_get_boxed (&val);
  CHECK (arr != NULL);
  CHECK (arr->len == 1);
  CHECK (strcmp ((const char *) arr->pdata[0], "consumer") == 0);
  g_value_unset (&val);

  /* 4. DBusError -> GError mapping layer, mirroring upstream
   *    test/errors.c (which passed on this device): the conversion
   *    through dbus_set_g_error maps the wire name onto the
   *    DBUS_GERROR domain and carries the message through. */
  {
    DBusError derror;
    GError *gerror = NULL;

    dbus_error_init (&derror);
    dbus_set_error_const (&derror, DBUS_ERROR_NO_MEMORY, "Out of memory!");
    dbus_set_g_error (&gerror, &derror);
    CHECK (gerror != NULL);
    CHECK (gerror->domain == DBUS_GERROR);
    CHECK (gerror->code == DBUS_GERROR_NO_MEMORY);
    CHECK (strcmp (gerror->message, "Out of memory!") == 0);
    g_clear_error (&gerror);
    dbus_error_free (&derror);
  }

  printf ("dbus-glib test_package: all checks passed\n");
  return 0;
}
