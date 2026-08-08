#include <gtkmacintegration/gtkosxapplication.h>

#include <glib.h>

static void did_become_active(GtkosxApplication *app, gpointer user_data)
{
    guint *count = user_data;
    (void)app;
    (*count)++;
}

int main(void)
{
    GtkosxApplication *app = gtkosx_application_get();
    GtkosxApplication *same_app = gtkosx_application_get();
    GtkosxApplicationClass *app_class;
    guint activation_count = 0;
    gchar *bundle_path = NULL;
    gchar *resource_path = NULL;
    gchar *executable_path = NULL;
    gchar *bundle_id = NULL;
    gchar *bundle_info_id = NULL;
    gint critical_request;
    gint info_request;

    if (app == NULL) {
        return 1;
    }
    if (same_app != app) {
        return 2;
    }
    app_class = GTKOSX_APPLICATION_GET_CLASS(app);
    if (app_class == NULL ||
        !GTKOSX_IS_APPLICATION_CLASS(app_class) ||
        GTKOSX_APPLICATION_CLASS(app_class) != app_class) {
        return 11;
    }

    gtkosx_application_set_use_quartz_accelerators(app, FALSE);
    if (gtkosx_application_use_quartz_accelerators(app)) {
        return 3;
    }
    gtkosx_application_set_use_quartz_accelerators(app, TRUE);
    if (!gtkosx_application_use_quartz_accelerators(app)) {
        return 4;
    }

    g_signal_connect(
        app,
        "NSApplicationDidBecomeActive",
        G_CALLBACK(did_become_active),
        &activation_count
    );
    gtkosx_application_ready(app);
    gtkosx_application_ready(app);
    if (activation_count != 1) {
        return 5;
    }

    critical_request = gtkosx_application_attention_request(
        app, GTKOSX_APPLICATION_ATTENTION_TYPE_CRITICAL_REQUEST
    );
    info_request = gtkosx_application_attention_request(
        app, GTKOSX_APPLICATION_ATTENTION_TYPE_INFO_REQUEST
    );
    if (critical_request <= 0 || info_request <= critical_request) {
        return 6;
    }
    gtkosx_application_cancel_attention_request(app, critical_request);
    gtkosx_application_cancel_attention_request(app, info_request);

    bundle_path = gtkosx_application_get_bundle_path();
    resource_path = gtkosx_application_get_resource_path();
    executable_path = gtkosx_application_get_executable_path();
    if (bundle_path == NULL || bundle_path[0] == '\0') {
        g_free(bundle_path);
        g_free(resource_path);
        g_free(executable_path);
        return 7;
    }
    if (resource_path == NULL || resource_path[0] == '\0') {
        g_free(bundle_path);
        g_free(resource_path);
        g_free(executable_path);
        return 8;
    }
    if (executable_path == NULL || executable_path[0] == '\0') {
        g_free(bundle_path);
        g_free(resource_path);
        g_free(executable_path);
        return 9;
    }

    g_setenv("OHOS_BUNDLE_NAME", "gtk-mac-integration-test", TRUE);
    g_set_application_name("gtk-mac-integration-test");
    bundle_id = gtkosx_application_get_bundle_id();
    bundle_info_id = gtkosx_application_get_bundle_info("CFBundleIdentifier");
    if (g_strcmp0(bundle_id, "gtk-mac-integration-test") != 0 ||
        g_strcmp0(bundle_info_id, bundle_id) != 0) {
        g_free(bundle_path);
        g_free(resource_path);
        g_free(executable_path);
        g_free(bundle_id);
        g_free(bundle_info_id);
        return 10;
    }

    g_free(bundle_path);
    g_free(resource_path);
    g_free(executable_path);
    g_free(bundle_id);
    g_free(bundle_info_id);
    return 0;
}
