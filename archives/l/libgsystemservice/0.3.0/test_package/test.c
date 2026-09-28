/* -*- mode: C; c-file-style: "gnu"; indent-tabs-mode: nil; -*- */
/*
 * Consumer-side smoke test for libgsystemservice 0.3.0 on HarmonyOS PC.
 *
 * It deliberately stays bus-free: everything asserted here is reachable
 * without a D-Bus connection, so the test is an honest check that a *consumer*
 * can link against the installed library and use its public API.  The upstream
 * suite (run inside the recipe's build()) covers the bus-dependent paths.
 *
 * Covered:
 *   - GObject type registration (final class, derivable class, interface)
 *   - the two public error domains and the exit-status mapping
 *   - GssConfigFile: path list beats the resource-backed default, per-key
 *     fallback to the default, strv/boolean/string/uint getters, range
 *     validation, group de-duplication + sorting, error reporting for a
 *     malformed file
 *   - GssService: subclassing the derivable class, property round trips,
 *     and the "nothing has run yet" state of the bus-facing getters
 */
#include <gio/gio.h>
#include <glib.h>
#include <glib/gstdio.h>
#include <locale.h>
#include <string.h>

#include <libgsystemservice/config-file.h>
#include <libgsystemservice/peer-manager.h>
#include <libgsystemservice/service.h>

/* Generated from config.gresource.xml by glib-compile-resources with
 * --generate-source --c-name=consumer_resources (see conanfile.py). */
extern GResource *consumer_resources_get_resource (void);

#define DEFAULT_CONFIG_PATH "/org/ohos/libgsystemservice/consumer/config.ini"

static guint checks_run = 0;
static guint checks_failed = 0;

#define CHECK(cond) G_STMT_START {                                      \
    checks_run++;                                                       \
    if (!(cond)) {                                                      \
      checks_failed++;                                                  \
      g_printerr ("FAIL %s:%d: %s\n", __FILE__, __LINE__, #cond);       \
    }                                                                   \
  } G_STMT_END

/* ─────────── a minimal GssService subclass ───────────
 * GssServiceClass documents startup_async / startup_finish / shutdown as
 * mandatory for every implementation, so a consumer must be able to fill in
 * those three vfuncs and be constructed. */
#define TEST_TYPE_SERVICE test_service_get_type ()
G_DECLARE_FINAL_TYPE (TestService, test_service, TEST, SERVICE, GssService)

struct _TestService
{
  GssService parent;
};

G_DEFINE_TYPE (TestService, test_service, GSS_TYPE_SERVICE)

static void
test_service_startup_async (GssService          *self,
                            GCancellable        *cancellable,
                            GAsyncReadyCallback  callback,
                            gpointer             user_data)
{
  g_autoptr(GTask) task = g_task_new (self, cancellable, callback, user_data);
  g_task_return_boolean (task, TRUE);
}

static void
test_service_startup_finish (GssService    *self,
                             GAsyncResult  *result,
                             GError       **error)
{
  g_task_propagate_boolean (G_TASK (result), error);
}

static void
test_service_shutdown (GssService *self)
{
}

static void
test_service_class_init (TestServiceClass *klass)
{
  GssServiceClass *service_class = GSS_SERVICE_CLASS (klass);

  service_class->startup_async = test_service_startup_async;
  service_class->startup_finish = test_service_startup_finish;
  service_class->shutdown = test_service_shutdown;
}

static void
test_service_init (TestService *self)
{
}

/* ─────────── type registration ─────────── */
static void
check_type_registration (void)
{
  CHECK (gss_config_file_get_type () != 0);
  CHECK (gss_service_get_type () != 0);
  CHECK (gss_peer_manager_get_type () != 0);

  CHECK (g_type_is_a (GSS_TYPE_CONFIG_FILE, G_TYPE_OBJECT));
  CHECK (g_type_is_a (GSS_TYPE_SERVICE, G_TYPE_OBJECT));
  /* GssPeerManager is an interface, not a class: implementors provide the
   * credentials lookups, the library only declares the contract. */
  CHECK (G_TYPE_IS_INTERFACE (GSS_TYPE_PEER_MANAGER));
}

/* ─────────── error domains ─────────── */
static void
check_error_domains (void)
{
  g_autoptr(GError) error = NULL;
  guint i;

  CHECK (gss_service_error_quark () != 0);
  CHECK (gss_peer_manager_error_quark () != 0);
  CHECK (gss_service_error_quark () != gss_peer_manager_error_quark ());

  /* Every service error must map to a non-zero process exit status. */
  for (i = GSS_SERVICE_ERROR_SIGNALLED; i <= GSS_SERVICE_ERROR_TIMEOUT; i++)
    CHECK (gss_service_error_to_exit_status ((GssServiceError) i) != 0);

  error = g_error_new_literal (GSS_SERVICE_ERROR, GSS_SERVICE_ERROR_TIMEOUT,
                               "inactivity timeout");
  CHECK (g_error_matches (error, GSS_SERVICE_ERROR, GSS_SERVICE_ERROR_TIMEOUT));
  CHECK (!g_error_matches (error, GSS_PEER_MANAGER_ERROR,
                           GSS_PEER_MANAGER_ERROR_IDENTIFYING_PEER));
}

/* ─────────── GssConfigFile ─────────── */
static gboolean
check_config_file (void)
{
  g_autoptr(GError) error = NULL;
  g_autoptr(GssConfigFile) config = NULL;
  g_autoptr(GssConfigFile) broken_config = NULL;
  g_autofree gchar *tmp_dir = NULL;
  g_autofree gchar *override_path = NULL;
  g_autofree gchar *broken_path = NULL;
  g_autofree gchar *missing_path = NULL;
  g_autofree gchar *name = NULL;
  g_auto(GStrv) list = NULL;
  g_auto(GStrv) groups = NULL;
  const gchar *paths[3];
  gsize n_elements = 0;
  gsize n_groups = 0;
  gboolean ok = FALSE;

  /* /tmp is not writable on the OHOS target; the recipe points TMPDIR at a
   * directory inside the build tree instead. */
  tmp_dir = g_dir_make_tmp ("libgsystemservice-consumer-XXXXXX", &error);
  if (tmp_dir == NULL)
    {
      g_printerr ("could not create a temporary directory: %s\n",
                  error->message);
      CHECK (FALSE);
      return FALSE;
    }

  override_path = g_build_filename (tmp_dir, "override.ini", NULL);
  broken_path = g_build_filename (tmp_dir, "broken.ini", NULL);
  missing_path = g_build_filename (tmp_dir, "missing.ini", NULL);

  CHECK (g_file_set_contents (override_path,
                              "[Test]\n"
                              "Number=2000\n"
                              "List=x;y\n",
                              -1, &error));
  g_clear_error (&error);
  CHECK (g_file_set_contents (broken_path,
                              "this line is not a valid key file\n",
                              -1, &error));
  g_clear_error (&error);

  /* The first three entries of `paths` are candidate files, in order; the
   * resource-backed default is consulted only after all of them. */
  paths[0] = missing_path;
  paths[1] = override_path;
  paths[2] = NULL;

  config = gss_config_file_new (paths, consumer_resources_get_resource (),
                                DEFAULT_CONFIG_PATH);
  CHECK (config != NULL);
  if (config == NULL)
    goto out;

  /* Precedence: the on-disk override wins over the default in the resource. */
  CHECK (gss_config_file_get_uint (config, "Test", "Number", 0, G_MAXUINT,
                                   &error) == 2000);
  CHECK (error == NULL);
  g_clear_error (&error);

  /* Keys the override does not mention fall back to the resource default. */
  CHECK (gss_config_file_get_boolean (config, "Test", "Flag", &error) == TRUE);
  CHECK (error == NULL);
  g_clear_error (&error);

  name = gss_config_file_get_string (config, "Test", "Name", &error);
  CHECK (error == NULL);
  CHECK (name != NULL);
  CHECK (name != NULL && strcmp (name, "default-name") == 0);
  g_clear_error (&error);

  /* Loaded from the override, so two elements, not the default's three. */
  list = gss_config_file_get_strv (config, "Test", "List", &n_elements, &error);
  CHECK (error == NULL);
  CHECK (n_elements == 2);
  CHECK (list != NULL && list[0] != NULL && strcmp (list[0], "x") == 0);
  CHECK (list != NULL && list[1] != NULL && strcmp (list[1], "y") == 0);
  CHECK (list != NULL && list[2] == NULL);
  g_clear_error (&error);

  /* Reverse control: a value outside [min, max] is rejected, not clamped. */
  CHECK (gss_config_file_get_uint (config, "Test", "Number", 5000, 6000,
                                   &error) == 0);
  CHECK (g_error_matches (error, G_KEY_FILE_ERROR,
                          G_KEY_FILE_ERROR_INVALID_VALUE));
  g_clear_error (&error);

  /* Groups are de-duplicated across all files and sorted lexicographically. */
  groups = gss_config_file_get_groups (config, &n_groups, &error);
  CHECK (error == NULL);
  CHECK (n_groups == 2);
  CHECK (groups != NULL && groups[0] != NULL &&
         strcmp (groups[0], "DefaultOnly") == 0);
  CHECK (groups != NULL && groups[1] != NULL &&
         strcmp (groups[1], "Test") == 0);
  g_clear_error (&error);

  /* Reverse control: a malformed candidate file surfaces a parse error
   * instead of being treated as "no value". */
  paths[0] = broken_path;
  paths[1] = override_path;
  broken_config = gss_config_file_new (paths, consumer_resources_get_resource (),
                                       DEFAULT_CONFIG_PATH);
  CHECK (broken_config != NULL);
  if (broken_config != NULL)
    {
      CHECK (gss_config_file_get_uint (broken_config, "Test", "Number", 0,
                                       G_MAXUINT, &error) == 0);
      CHECK (g_error_matches (error, G_KEY_FILE_ERROR, G_KEY_FILE_ERROR_PARSE));
      g_clear_error (&error);
    }

  ok = TRUE;

out:
  g_remove (override_path);
  g_remove (broken_path);
  g_rmdir (tmp_dir);
  return ok;
}

/* ─────────── GssService ─────────── */
static void
check_service (void)
{
  g_autoptr(GssService) service = NULL;
  g_autofree gchar *service_id = NULL;

  service = g_object_new (TEST_TYPE_SERVICE,
                          "service-id",
                          "org.ohos.libgsystemservice.consumer.TestService",
                          "translation-domain", "libgsystemservice-consumer",
                          "inactivity-timeout", (guint) 30000,
                          NULL);
  CHECK (service != NULL);
  if (service == NULL)
    return;

  CHECK (GSS_IS_SERVICE (service));
  CHECK (g_type_is_a (G_OBJECT_TYPE (service), GSS_TYPE_SERVICE));

  g_object_get (service, "service-id", &service_id, NULL);
  CHECK (service_id != NULL);
  CHECK (service_id != NULL &&
         strcmp (service_id,
                 "org.ohos.libgsystemservice.consumer.TestService") == 0);

  CHECK (gss_service_get_inactivity_timeout (service) == 30000);
  gss_service_set_inactivity_timeout (service, 45000);
  CHECK (gss_service_get_inactivity_timeout (service) == 45000);

  /* gss_service_run() has not been called, so all of these must report the
   * "unset" value rather than garbage. */
  CHECK (gss_service_get_dbus_connection (service) == NULL);
  CHECK (gss_service_get_exit_signal (service) == 0);
  CHECK (gss_service_get_debug_controller (service) == NULL);
}

int
main (int    argc,
      char **argv)
{
  setlocale (LC_ALL, "");

  check_type_registration ();
  check_error_domains ();
  check_config_file ();
  check_service ();

  g_print ("libgsystemservice 0.3.0 consumer test: %u checks, %u failed\n",
           checks_run, checks_failed);

  return (checks_failed == 0) ? 0 : 1;
}
