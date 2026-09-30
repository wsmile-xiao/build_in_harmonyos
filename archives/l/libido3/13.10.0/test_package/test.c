/* test_package/test.c — libido3 13.10.0 OHOS consumer test.
 *
 * 5 checks, each printing one "checkN OK" line on success:
 *   1. ido_init() runs (compiled with USE_UBUNTU_PRIVATE_API disabled, the
 *      body is a no-op, but the symbol must exist and be callable).
 *   2. OHOS adaptation point: the Ubuntu GTK private-API factory is NOT
 *      compiled in — ido_menu_item_factory_get_type must be ABSENT from the
 *      linked library (dlsym fails). On a vanilla Ubuntu build this symbol
 *      exists, so a regression back to the ubuntu-private build fails here.
 *   3. IdoTimeline (pure GObject) instantiates headless — exercises the
 *      glib-mkenums generated idotypebuiltins registration path.
 *   4. IdoSwitchMenuItem widget constructs after gtk_init on the headless
 *      broadway backend.
 *   5. IdoEntryMenuItem widget constructs (GTK3 menu item subclass from the
 *      installed headers).
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>

#include <gtk/gtk.h>
#include <libido/libido.h>
#include <libido/idotimeline.h>
#include <libido/idoswitchmenuitem.h>
#include <libido/idoentrymenuitem.h>

int
main (int argc, char **argv)
{
  int failures = 0;

  /* check 1: ido_init() callable */
  ido_init ();
  printf ("check1 OK: ido_init\n");

  /* check 2: ubuntu-private API disabled on OHOS */
  if (dlsym (RTLD_DEFAULT, "ido_menu_item_factory_get_type") != NULL)
    {
      printf ("check2 FAIL: ido_menu_item_factory_get_type exported — "
              "ubuntu-private build leaked into the OHOS package\n");
      failures++;
    }
  else
    {
      printf ("check2 OK: ubuntu-private API disabled on OHOS\n");
    }

  /* check 3: IdoTimeline instantiation (headless, pure GObject) */
  {
    IdoTimeline *timeline = ido_timeline_new (500);
    if (timeline != NULL &&
        g_str_equal (g_type_name (G_TYPE_FROM_INSTANCE (timeline)),
                     "IdoTimeline"))
      printf ("check3 OK: IdoTimeline\n");
    else
      {
        printf ("check3 FAIL: IdoTimeline instantiation\n");
        failures++;
      }
    if (timeline)
      g_object_unref (timeline);
  }

  /* checks 4-5 need a GDK backend; CI serves the headless broadway backend
   * via broadwayd (gtk package). */
  if (!gtk_init_check (&argc, &argv))
    {
      printf ("check4 FAIL: no display backend for gtk_init\n");
      printf ("check5 FAIL: no display backend for gtk_init\n");
      return 1;
    }

  {
    GtkWidget *item = ido_switch_menu_item_new ();
    if (item != NULL && GTK_IS_MENU_ITEM (item))
      printf ("check4 OK: IdoSwitchMenuItem\n");
    else
      {
        printf ("check4 FAIL: IdoSwitchMenuItem instantiation\n");
        failures++;
      }
    if (item)
      g_object_unref (item);
  }

  {
    GtkWidget *item = ido_entry_menu_item_new ();
    if (item != NULL && GTK_IS_MENU_ITEM (item))
      printf ("check5 OK: IdoEntryMenuItem\n");
    else
      {
        printf ("check5 FAIL: IdoEntryMenuItem instantiation\n");
        failures++;
      }
    if (item)
      g_object_unref (item);
  }

  return failures == 0 ? 0 : 1;
}
