#include <gio/gio.h>
#include <glib-object.h>
#include <girepository/girepository.h>
#include <gmodule.h>

#include <stdio.h>
#include <string.h>

static gpointer
thread_entry (gpointer data)
{
  return data;
}

int
main (void)
{
  const gchar payload[] = "hello glib";
  gchar buffer[sizeof payload] = { 0 };
  GError *error = NULL;
  GInputStream *stream = NULL;
  GObject *object = NULL;
  GIRepository *repository = NULL;
  GThread *thread = NULL;
  gchar *module_path = NULL;
  const char * const *search_paths;
  const char repository_path[] = "/glib2-consumer-girepository";
  size_t n_search_paths = 0;
  gssize bytes_read;
  int result = 1;

  if (!g_regex_match_simple ("^hello [a-z]+$", payload, 0, 0))
    goto cleanup;

  stream = g_memory_input_stream_new_from_data (payload, sizeof payload, NULL);
  bytes_read = g_input_stream_read (stream, buffer, sizeof buffer, NULL, &error);
  if (bytes_read != sizeof payload || error != NULL ||
      memcmp (buffer, payload, sizeof payload) != 0)
    goto cleanup;

  object = g_object_new (G_TYPE_OBJECT, NULL);
  if (!G_IS_OBJECT (object))
    goto cleanup;

  repository = gi_repository_new ();
  if (!GI_IS_REPOSITORY (repository))
    goto cleanup;
  gi_repository_prepend_search_path (repository, repository_path);
  search_paths = gi_repository_get_search_path (repository, &n_search_paths);
  if (n_search_paths == 0 || strcmp (search_paths[0], repository_path) != 0)
    goto cleanup;

  module_path = g_module_build_path (NULL, "glib2_consumer_probe");
  if (module_path == NULL || module_path[0] == '\0')
    goto cleanup;

  thread = g_thread_new ("glib2-consumer", thread_entry, object);
  if (g_thread_join (thread) != object)
    {
      thread = NULL;
      goto cleanup;
    }
  thread = NULL;

  if (g_log_writer_is_journald (-1))
    goto cleanup;

  puts ("GLIB2_CONSUMER_PASS=12/12");
  result = 0;

cleanup:
  if (thread != NULL)
    g_thread_join (thread);
  g_clear_error (&error);
  g_free (module_path);
  g_clear_object (&repository);
  g_clear_object (&object);
  g_clear_object (&stream);
  return result;
}
