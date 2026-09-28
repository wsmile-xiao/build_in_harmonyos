/* SPDX-License-Identifier: LGPL-2.1-or-later
 *
 * Consumer test for the packaged libgspell-1 on HarmonyOS PC.
 *
 * It exercises the *installed* shared library through its public headers and
 * prints TAP (see test_package/conanfile.py, which turns the lines into the
 * package-level test result).
 *
 * Two behaviours are specific to this platform and are asserted explicitly
 * rather than worked around:
 *
 *  1. enchant/2.8.2 on ohpcd is built with every provider disabled, so
 *     `gspell_language_get_available()` is empty and
 *     `gspell_language_lookup("en_US")` returns NULL.  gspell's documented
 *     contract is that `gspell_checker_check_word()` then returns TRUE
 *     ("limit the damage" - gspell-checker.c) instead of failing, and
 *     `gspell_checker_get_suggestions()` returns NULL.  Both are asserted.
 *  2. The library must be usable without ever constructing a dictionary:
 *     the GtkEntry / GtkTextBuffer / GtkTextView integrations have to attach
 *     and round-trip regardless of dictionary availability.
 *
 * gtk_init() needs a GDK backend; the driver runs this under the headless
 * broadway backend (GDK_BACKEND=broadway + broadwayd from the gtk package).
 */

#include <gtk/gtk.h>
#include <gspell/gspell.h>

static int total = 0;
static int failed = 0;

static void
check (gboolean    condition,
       const char *description)
{
	total++;
	if (condition)
	{
		g_print ("ok %d - %s\n", total, description);
	}
	else
	{
		failed++;
		g_print ("not ok %d - %s\n", total, description);
	}
}

int
main (int    argc,
      char **argv)
{
	GspellChecker *checker;
	GspellLanguage *language;
	const GList *available;
	GtkWidget *entry;
	GtkWidget *text_view;
	GtkTextBuffer *gtk_buffer;
	GspellTextBuffer *gspell_buffer;
	GspellTextView *gspell_view;
	GspellEntry *gspell_entry;
	GspellNavigator *navigator;
	GError *error = NULL;
	GSList *suggestions;
	gboolean no_dictionary;

	gtk_init (&argc, &argv);

	/* --- the library is reachable and initialises --------------------- */
	check (gspell_checker_error_quark () != 0,
	       "gspell_checker_error_quark() is available from libgspell-1");

	available = gspell_language_get_available ();
	check (available == NULL ||
	       gspell_language_get_code (available->data) != NULL,
	       "gspell_language_get_available() yields describable GspellLanguage items (or an empty list)");

	no_dictionary = (available == NULL);

	/* --- language lookup matches the installed dictionary set --------- */
	language = (GspellLanguage *) gspell_language_lookup ("en_US");
	if (no_dictionary)
	{
		check (language == NULL,
		       "with no Enchant provider installed, gspell_language_lookup(\"en_US\") returns NULL");
	}
	else
	{
		check (language != NULL &&
		       gspell_language_get_code (language) != NULL &&
		       gspell_language_get_name (language) != NULL,
		       "with dictionaries installed, gspell_language_lookup(\"en_US\") yields a named language");
	}

	/* --- checker lifecycle ------------------------------------------- */
	checker = gspell_checker_new (NULL);
	check (checker != NULL && GSPELL_IS_CHECKER (checker),
	       "gspell_checker_new(NULL) builds a GspellChecker");

	/* Upstream contract (gspell-checker.c): no dictionary => TRUE. */
	check (gspell_checker_check_word (checker, "hxllx", -1, &error) == TRUE &&
	       error == NULL,
	       "gspell_checker_check_word() falls back to TRUE without raising an error when no dictionary is active");

	suggestions = gspell_checker_get_suggestions (checker, "helo", -1);
	if (no_dictionary)
	{
		check (suggestions == NULL,
		       "gspell_checker_get_suggestions() returns NULL when no dictionary is active");
	}
	else
	{
		check (suggestions != NULL,
		       "gspell_checker_get_suggestions() returns a suggestion list when a dictionary is active");
	}
	if (suggestions != NULL)
	{
		g_slist_free_full (suggestions, g_free);
	}

	/* --- GtkTextBuffer integration ----------------------------------- */
	gtk_buffer = gtk_text_buffer_new (NULL);
	gspell_buffer = gspell_text_buffer_get_from_gtk_text_buffer (gtk_buffer);
	check (gspell_buffer != NULL && GSPELL_IS_TEXT_BUFFER (gspell_buffer),
	       "gspell_text_buffer_get_from_gtk_text_buffer() attaches a GspellTextBuffer to a GtkTextBuffer");
	check (gspell_text_buffer_get_buffer (gspell_buffer) == gtk_buffer,
	       "gspell_text_buffer_get_buffer() round-trips to the same GtkTextBuffer");

	/* --- GtkTextView integration ------------------------------------- */
	text_view = gtk_text_view_new ();
	gspell_view = gspell_text_view_get_from_gtk_text_view (GTK_TEXT_VIEW (text_view));
	check (gspell_view != NULL && GSPELL_IS_TEXT_VIEW (gspell_view),
	       "gspell_text_view_get_from_gtk_text_view() attaches a GspellTextView to a GtkTextView");
	check (gspell_text_view_get_view (gspell_view) == GTK_TEXT_VIEW (text_view),
	       "gspell_text_view_get_view() round-trips to the same GtkTextView");

	navigator = gspell_navigator_text_view_new (GTK_TEXT_VIEW (text_view));
	check (navigator != NULL && GSPELL_IS_NAVIGATOR (navigator),
	       "gspell_navigator_text_view_new() builds a navigator for a GtkTextView");

	/* --- GtkEntry integration ---------------------------------------- */
	entry = gtk_entry_new ();
	gspell_entry = gspell_entry_get_from_gtk_entry (GTK_ENTRY (entry));
	check (gspell_entry != NULL && GSPELL_IS_ENTRY (gspell_entry),
	       "gspell_entry_get_from_gtk_entry() attaches a GspellEntry to a GtkEntry");

	gspell_entry_set_inline_spell_checking (gspell_entry, TRUE);
	check (gspell_entry_get_inline_spell_checking (gspell_entry) == TRUE,
	       "the inline-spell-checking flag round-trips through GspellEntry");

	g_print ("1..%d\n", total);

	/* GspellTextBuffer / GspellTextView / GspellEntry are owned by the widget
	 * they were attached to (g_object_set_data_full), so they are not
	 * unreffed here; teardown order is left to the widgets. */
	g_object_unref (checker);
	g_object_unref (gtk_buffer);
	gtk_widget_destroy (text_view);
	gtk_widget_destroy (entry);

	return failed == 0 ? 0 : 1;
}
