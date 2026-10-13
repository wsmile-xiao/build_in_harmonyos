/*
 * test_libedataserverui4.c — functional smoke test for libedataserverui4-1.0
 *
 * The test links against libedataserverui4-1.0.so (which in turn pulls the
 * private EDS libraries libcamel-1.2 / libecal-2.0 / libedataserver-1.2 /
 * libedbus-private) and exercises real library entry points:
 *
 *   - the GType registration path of every public class of the library
 *     (ECredentialsPrompter, ECredentialsPrompterImpl,
 *      ECredentialsPrompterImplPassword, ECellRendererColor,
 *      ECertificateWidget, ERemindersWidget, EWebDAVDiscoverDialog,
 *      EWebDAVDiscoverContent) — this executes the per-class
 *     class_init/instance_init code compiled into the library;
 *   - instantiation of a library subclass and its public accessor
 *     (e_cell_renderer_color_new + E_IS_CELL_RENDERER_COLOR), released again
 *     with g_object_unref().
 *
 * Exit code 0 means every call behaved as documented.
 */
#include <libedataserverui4/libedataserverui4.h>

#include <stdio.h>

static int failures = 0;

static void
check_object_type (const char *label, GType type)
{
	printf ("%-42s %s\n", label, g_type_name (type));

	if (type == G_TYPE_INVALID) {
		fprintf (stderr, "FAIL: %s returned 0\n", label);
		failures++;
		return;
	}
	if (!g_type_is_a (type, G_TYPE_OBJECT)) {
		fprintf (stderr, "FAIL: %s is not a GObject subclass\n", label);
		failures++;
	}
}

static void
check_type_is_a (const char *label, GType type, GType base, const char *base_name)
{
	check_object_type (label, type);

	if (type != G_TYPE_INVALID && !g_type_is_a (type, base)) {
		fprintf (stderr, "FAIL: %s is not a %s subclass\n", label, base_name);
		failures++;
	}
}

int
main (void)
{
	GtkCellRenderer *renderer;

	/* GType registration of the public classes. */
	check_object_type ("e_credentials_prompter_get_type",
			   e_credentials_prompter_get_type ());
	check_object_type ("e_credentials_prompter_impl_get_type",
			   e_credentials_prompter_impl_get_type ());
	check_object_type ("e_credentials_prompter_impl_password_get_type",
			   e_credentials_prompter_impl_password_get_type ());
	/* GtkCellRenderer is a plain GObject in GTK4, not a GtkWidget. */
	check_type_is_a ("e_cell_renderer_color_get_type",
			 e_cell_renderer_color_get_type (),
			 GTK_TYPE_CELL_RENDERER, "GtkCellRenderer");
	check_type_is_a ("e_certificate_widget_get_type",
			 e_certificate_widget_get_type (),
			 GTK_TYPE_WIDGET, "GtkWidget");
	check_type_is_a ("e_reminders_widget_get_type",
			 e_reminders_widget_get_type (),
			 GTK_TYPE_WIDGET, "GtkWidget");
	check_type_is_a ("e_webdav_discover_dialog_get_type",
			 e_webdav_discover_dialog_get_type (),
			 GTK_TYPE_DIALOG, "GtkDialog");
	check_type_is_a ("e_webdav_discover_content_get_type",
			 e_webdav_discover_content_get_type (),
			 GTK_TYPE_WIDGET, "GtkWidget");

	/* Instantiate a library subclass and use its public accessor. */
	renderer = e_cell_renderer_color_new ();
	printf ("%-42s %s\n", "e_cell_renderer_color_new()",
		renderer ? G_OBJECT_TYPE_NAME (renderer) : "()");

	if (renderer == NULL) {
		fprintf (stderr, "FAIL: e_cell_renderer_color_new() returned NULL\n");
		failures++;
	} else {
		if (!E_IS_CELL_RENDERER_COLOR (renderer)) {
			fprintf (stderr, "FAIL: instance is not an ECellRendererColor\n");
			failures++;
		}
		if (!GTK_IS_CELL_RENDERER (renderer)) {
			fprintf (stderr, "FAIL: instance is not a GtkCellRenderer\n");
			failures++;
		}
		g_object_unref (renderer);
	}

	if (failures > 0) {
		fprintf (stderr, "FAIL: %d check(s) failed\n", failures);
		return 1;
	}

	printf ("PASS: libedataserverui4 API calls succeeded\n");
	return 0;
}
