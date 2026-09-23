/* Consumer test for template-glib: parse a template through the public
 * TmplTemplate API, inject a variable via TmplScope, expand it, and assert
 * the rendered output. Real API calls with a behavioral assertion — not a
 * print-only / link-only stub. (Template syntax is {{expr}}, scope is a
 * boxed type freed with tmpl_scope_unref.) */
#include <tmpl-glib.h>
#include <stdio.h>
#include <string.h>

int
main (int argc,
      char *argv[])
{
  TmplTemplate *tpl;
  TmplScope *scope;
  GError *error = NULL;
  gchar *rendered;
  int status = 0;

  tpl = tmpl_template_new (NULL);
  if (!tmpl_template_parse_string (tpl, "Hello {{name}}!", &error))
    {
      fprintf (stderr, "parse failed: %s\n", error->message);
      return 1;
    }

  scope = tmpl_scope_new ();
  tmpl_scope_set_string (scope, "name", "HarmonyOS");

  rendered = tmpl_template_expand_string (tpl, scope, &error);
  if (rendered == NULL)
    {
      fprintf (stderr, "expand failed: %s\n", error->message);
      return 1;
    }

  printf ("rendered: %s\n", rendered);
  if (strcmp (rendered, "Hello HarmonyOS!") != 0)
    {
      fprintf (stderr, "unexpected render output: %s\n", rendered);
      status = 1;
    }

  g_free (rendered);
  tmpl_scope_unref (scope);
  g_object_unref (tpl);

  return status;
}
