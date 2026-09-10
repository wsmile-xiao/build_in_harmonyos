#include <libwnck/libwnck.h>
#include <glib-object.h>
#include <X11/Xlib.h>
#include <stdio.h>
#include <stdlib.h>

static int
require_true (int condition, const char *message)
{
  if (!condition)
    {
      fprintf (stderr, "FAIL: %s\n", message);
      return 0;
    }
  return 1;
}

static WnckWindow *
wait_for_window (WnckHandle *handle, Window xid, gboolean present)
{
  gint64 deadline = g_get_monotonic_time () + 5 * G_TIME_SPAN_SECOND;
  WnckWindow *window;

  do
    {
      while (g_main_context_iteration (NULL, FALSE))
        ;
      window = wnck_handle_get_window (handle, xid);
      if ((window != NULL) == present)
        return window;
      g_usleep (10 * 1000);
    }
  while (g_get_monotonic_time () < deadline);

  return wnck_handle_get_window (handle, xid);
}

int
main (void)
{
  WnckHandle *handle;
  WnckScreen *screen;
  int assertions = 0;
  int expected = 15;

  assertions += require_true (WNCK_MAJOR_VERSION == 43, "major version");
  assertions += require_true (WNCK_MINOR_VERSION == 3, "minor version");
  assertions += require_true (WNCK_MICRO_VERSION == 0, "micro version");
  assertions += require_true (WNCK_CHECK_VERSION (43, 3, 0), "version check");
  assertions += require_true (wnck_handle_get_type () != G_TYPE_INVALID,
                              "WnckHandle type registration");
  assertions += require_true (wnck_screen_get_type () != G_TYPE_INVALID,
                              "WnckScreen type registration");
  assertions += require_true (wnck_window_get_type () != G_TYPE_INVALID,
                              "WnckWindow type registration");
  assertions += require_true (wnck_application_get_type () != G_TYPE_INVALID,
                              "WnckApplication type registration");
  assertions += require_true (wnck_workspace_get_type () != G_TYPE_INVALID,
                              "WnckWorkspace type registration");
  assertions += require_true (wnck_pager_get_type () != G_TYPE_INVALID,
                              "WnckPager type registration");
  assertions += require_true (wnck_tasklist_get_type () != G_TYPE_INVALID,
                              "WnckTasklist type registration");
  assertions += require_true (wnck_selector_get_type () != G_TYPE_INVALID,
                              "WnckSelector type registration");

  handle = wnck_handle_new (WNCK_CLIENT_TYPE_PAGER);
  assertions += require_true (handle != NULL, "construct WnckHandle");
  if (handle != NULL)
    {
      wnck_handle_set_default_icon_size (handle, 48);
      wnck_handle_set_default_mini_icon_size (handle, 24);
      assertions += 2;

      if (getenv ("LIBWNCK_TEST_X11") != NULL)
        {
          expected += 11;
          screen = wnck_handle_get_default_screen (handle);
          assertions += require_true (screen != NULL, "default X11 screen");
          if (screen != NULL)
            {
              wnck_screen_force_update (screen);
              assertions += require_true (wnck_screen_get_number (screen) == 0,
                                          "X11 screen number");
              assertions += require_true (wnck_screen_get_width (screen) == 1280,
                                          "X11 screen width");
              assertions += require_true (wnck_screen_get_height (screen) == 720,
                                          "X11 screen height");
              assertions += require_true (wnck_screen_get_workspace_count (screen) >= 1,
                                          "EWMH workspace count");
              assertions += require_true (wnck_screen_get_workspace (screen, 0) != NULL,
                                          "first workspace");
              assertions += require_true (
                  wnck_screen_get_window_manager_name (screen) != NULL,
                  "EWMH window manager name");

              {
                Display *display = XOpenDisplay (NULL);
                assertions += require_true (display != NULL,
                                            "open test X11 connection");
                if (display != NULL)
                  {
                    Window xid;
                    WnckWindow *window;

                    xid = XCreateSimpleWindow (
                        display, DefaultRootWindow (display), 20, 20,
                        160, 90, 0, 0, WhitePixel (display,
                                                   DefaultScreen (display)));
                    XStoreName (display, xid, "libwnck3-event-bridge-test");
                    XMapWindow (display, xid);
                    XFlush (display);

                    window = wait_for_window (handle, xid, TRUE);
                    assertions += require_true (window != NULL,
                                                "dynamic window-open event");
                    assertions += require_true (
                        window != NULL && wnck_window_get_name (window) != NULL,
                        "dynamic window property load");

                    XDestroyWindow (display, xid);
                    XFlush (display);
                    assertions += require_true (
                        wait_for_window (handle, xid, FALSE) == NULL,
                        "dynamic window-close event");
                    XCloseDisplay (display);
                  }
              }
            }
        }
      g_object_unref (handle);
    }

  if (assertions != expected)
    return 1;
  printf ("libwnck3 consumer assertions: %d/%d passed\n", assertions, expected);
  return 0;
}
