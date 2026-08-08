#include "gtkosxapplication.h"

#include <glib.h>

enum {
    DID_BECOME_ACTIVE,
    WILL_RESIGN_ACTIVE,
    BLOCK_TERMINATION,
    WILL_TERMINATE,
    OPEN_FILE,
    LAST_SIGNAL
};

static guint application_signals[LAST_SIGNAL];

struct _GtkosxApplication {
    GObject parent_instance;
    gboolean use_quartz_accelerators;
    gboolean ready;
    GtkMenuShell *menu_bar;
    GtkWidget *about_item;
    GtkMenuItem *window_menu;
    GtkMenuItem *help_menu;
    GtkMenuShell *dock_menu;
    GdkPixbuf *dock_icon_pixbuf;
    GPtrArray *app_menu_items;
    GHashTable *attention_requests;
    gchar *dock_icon_resource;
    guint menu_revision;
    gint next_attention_id;
};

struct _GtkosxApplicationClass {
    GObjectClass parent_class;
};

G_DEFINE_TYPE(GtkosxApplication, gtkosx_application, G_TYPE_OBJECT)

static void replace_object(gpointer *slot, gpointer value)
{
    if (*slot == value) {
        return;
    }
    if (value != NULL) {
        g_object_ref(value);
    }
    if (*slot != NULL) {
        g_object_unref(*slot);
    }
    *slot = value;
}

static void gtkosx_application_dispose(GObject *object)
{
    GtkosxApplication *self = GTKOSX_APPLICATION(object);

    replace_object((gpointer *)&self->menu_bar, NULL);
    replace_object((gpointer *)&self->about_item, NULL);
    replace_object((gpointer *)&self->window_menu, NULL);
    replace_object((gpointer *)&self->help_menu, NULL);
    replace_object((gpointer *)&self->dock_menu, NULL);
    replace_object((gpointer *)&self->dock_icon_pixbuf, NULL);
    g_clear_pointer(&self->app_menu_items, g_ptr_array_unref);

    G_OBJECT_CLASS(gtkosx_application_parent_class)->dispose(object);
}

static void gtkosx_application_finalize(GObject *object)
{
    GtkosxApplication *self = GTKOSX_APPLICATION(object);

    g_clear_pointer(&self->attention_requests, g_hash_table_unref);
    g_clear_pointer(&self->dock_icon_resource, g_free);

    G_OBJECT_CLASS(gtkosx_application_parent_class)->finalize(object);
}

static void gtkosx_application_class_init(GtkosxApplicationClass *klass)
{
    GObjectClass *object_class = G_OBJECT_CLASS(klass);

    object_class->dispose = gtkosx_application_dispose;
    object_class->finalize = gtkosx_application_finalize;

    application_signals[DID_BECOME_ACTIVE] = g_signal_new(
        "NSApplicationDidBecomeActive",
        GTKOSX_TYPE_APPLICATION,
        G_SIGNAL_NO_RECURSE | G_SIGNAL_ACTION,
        0,
        NULL,
        NULL,
        g_cclosure_marshal_VOID__VOID,
        G_TYPE_NONE,
        0
    );
    application_signals[WILL_RESIGN_ACTIVE] = g_signal_new(
        "NSApplicationWillResignActive",
        GTKOSX_TYPE_APPLICATION,
        G_SIGNAL_NO_RECURSE | G_SIGNAL_ACTION,
        0,
        NULL,
        NULL,
        g_cclosure_marshal_VOID__VOID,
        G_TYPE_NONE,
        0
    );
    application_signals[BLOCK_TERMINATION] = g_signal_new(
        "NSApplicationBlockTermination",
        GTKOSX_TYPE_APPLICATION,
        G_SIGNAL_NO_RECURSE | G_SIGNAL_ACTION,
        0,
        NULL,
        NULL,
        g_cclosure_marshal_generic,
        G_TYPE_BOOLEAN,
        0
    );
    application_signals[WILL_TERMINATE] = g_signal_new(
        "NSApplicationWillTerminate",
        GTKOSX_TYPE_APPLICATION,
        G_SIGNAL_NO_RECURSE | G_SIGNAL_ACTION,
        0,
        NULL,
        NULL,
        g_cclosure_marshal_VOID__VOID,
        G_TYPE_NONE,
        0
    );
    application_signals[OPEN_FILE] = g_signal_new(
        "NSApplicationOpenFile",
        GTKOSX_TYPE_APPLICATION,
        G_SIGNAL_NO_RECURSE | G_SIGNAL_ACTION,
        0,
        NULL,
        NULL,
        g_cclosure_marshal_generic,
        G_TYPE_BOOLEAN,
        1,
        G_TYPE_STRING
    );
}

static void gtkosx_application_init(GtkosxApplication *self)
{
    self->use_quartz_accelerators = TRUE;
    self->app_menu_items = g_ptr_array_new_with_free_func(g_object_unref);
    self->attention_requests = g_hash_table_new(g_direct_hash, g_direct_equal);
    self->next_attention_id = 1;
}

GtkosxApplication *gtkosx_application_get(void)
{
    static gsize instance_value;

    if (g_once_init_enter(&instance_value)) {
        GtkosxApplication *instance = g_object_new(GTKOSX_TYPE_APPLICATION, NULL);
        g_once_init_leave(&instance_value, (gsize)instance);
    }
    return (GtkosxApplication *)instance_value;
}

void gtkosx_application_ready(GtkosxApplication *self)
{
    g_return_if_fail(GTKOSX_IS_APPLICATION(self));
    if (!self->ready) {
        self->ready = TRUE;
        g_signal_emit(self, application_signals[DID_BECOME_ACTIVE], 0);
    }
}

void gtkosx_application_set_use_quartz_accelerators(
    GtkosxApplication *self, gboolean enabled
)
{
    g_return_if_fail(GTKOSX_IS_APPLICATION(self));
    self->use_quartz_accelerators = enabled;
}

gboolean gtkosx_application_use_quartz_accelerators(GtkosxApplication *self)
{
    g_return_val_if_fail(GTKOSX_IS_APPLICATION(self), FALSE);
    return self->use_quartz_accelerators;
}

void gtkosx_application_set_menu_bar(
    GtkosxApplication *self, GtkMenuShell *menu_shell
)
{
    g_return_if_fail(GTKOSX_IS_APPLICATION(self));
    g_return_if_fail(menu_shell == NULL || G_IS_OBJECT(menu_shell));
    replace_object((gpointer *)&self->menu_bar, menu_shell);
    self->menu_revision++;
}

void gtkosx_application_set_about_item(
    GtkosxApplication *self, GtkWidget *item
)
{
    g_return_if_fail(GTKOSX_IS_APPLICATION(self));
    g_return_if_fail(item == NULL || G_IS_OBJECT(item));
    replace_object((gpointer *)&self->about_item, item);
    self->menu_revision++;
}

void gtkosx_application_set_window_menu(
    GtkosxApplication *self, GtkMenuItem *menu_item
)
{
    g_return_if_fail(GTKOSX_IS_APPLICATION(self));
    g_return_if_fail(menu_item == NULL || G_IS_OBJECT(menu_item));
    replace_object((gpointer *)&self->window_menu, menu_item);
    self->menu_revision++;
}

void gtkosx_application_set_help_menu(
    GtkosxApplication *self, GtkMenuItem *menu_item
)
{
    g_return_if_fail(GTKOSX_IS_APPLICATION(self));
    g_return_if_fail(menu_item == NULL || G_IS_OBJECT(menu_item));
    replace_object((gpointer *)&self->help_menu, menu_item);
    self->menu_revision++;
}

void gtkosx_application_set_dock_menu(
    GtkosxApplication *self, GtkMenuShell *menu_shell
)
{
    g_return_if_fail(GTKOSX_IS_APPLICATION(self));
    g_return_if_fail(menu_shell == NULL || G_IS_OBJECT(menu_shell));
    replace_object((gpointer *)&self->dock_menu, menu_shell);
}

void gtkosx_application_set_dock_icon_pixbuf(
    GtkosxApplication *self, GdkPixbuf *pixbuf
)
{
    g_return_if_fail(GTKOSX_IS_APPLICATION(self));
    g_return_if_fail(pixbuf == NULL || G_IS_OBJECT(pixbuf));
    replace_object((gpointer *)&self->dock_icon_pixbuf, pixbuf);
    g_clear_pointer(&self->dock_icon_resource, g_free);
}

void gtkosx_application_sync_menubar(GtkosxApplication *self)
{
    g_return_if_fail(GTKOSX_IS_APPLICATION(self));
    self->menu_revision++;
}

void gtkosx_application_insert_app_menu_item(
    GtkosxApplication *self, GtkWidget *menu_item, gint index
)
{
    g_return_if_fail(GTKOSX_IS_APPLICATION(self));
    g_return_if_fail(menu_item != NULL && G_IS_OBJECT(menu_item));
    g_return_if_fail(index >= 0);

    if ((guint)index > self->app_menu_items->len) {
        index = (gint)self->app_menu_items->len;
    }
    g_ptr_array_insert(self->app_menu_items, index, g_object_ref(menu_item));
    self->menu_revision++;
}

void gtkosx_application_set_dock_icon_resource(
    GtkosxApplication *self,
    const gchar *name,
    const gchar *type,
    const gchar *subdir
)
{
    gchar *resource_path;
    gchar *filename;

    g_return_if_fail(GTKOSX_IS_APPLICATION(self));
    g_return_if_fail(name != NULL && *name != '\0');

    resource_path = gtkosx_application_get_resource_path();
    filename = type != NULL && *type != '\0'
        ? g_strdup_printf("%s.%s", name, type)
        : g_strdup(name);

    g_clear_pointer(&self->dock_icon_resource, g_free);
    self->dock_icon_resource = g_build_filename(
        resource_path,
        subdir != NULL ? subdir : "",
        filename,
        NULL
    );
    replace_object((gpointer *)&self->dock_icon_pixbuf, NULL);
    g_free(filename);
    g_free(resource_path);
}

gint gtkosx_application_attention_request(
    GtkosxApplication *self, GtkosxApplicationAttentionType type
)
{
    gint id;

    g_return_val_if_fail(GTKOSX_IS_APPLICATION(self), 0);
    g_return_val_if_fail(
        type == GTKOSX_APPLICATION_ATTENTION_TYPE_CRITICAL_REQUEST ||
        type == GTKOSX_APPLICATION_ATTENTION_TYPE_INFO_REQUEST,
        0
    );

    if (self->next_attention_id <= 0) {
        self->next_attention_id = 1;
    }
    id = self->next_attention_id;
    self->next_attention_id =
        id == G_MAXINT ? 1 : id + 1;
    g_hash_table_insert(
        self->attention_requests,
        GINT_TO_POINTER(id),
        GINT_TO_POINTER((gint)type + 1)
    );
    return id;
}

void gtkosx_application_cancel_attention_request(
    GtkosxApplication *self, gint id
)
{
    g_return_if_fail(GTKOSX_IS_APPLICATION(self));
    if (id > 0) {
        g_hash_table_remove(self->attention_requests, GINT_TO_POINTER(id));
    }
}

gchar *gtkosx_application_get_bundle_path(void)
{
    gchar *executable_path = gtkosx_application_get_executable_path();
    gchar *bundle_path;

    if (executable_path == NULL || *executable_path == '\0') {
        g_free(executable_path);
        return g_canonicalize_filename(".", NULL);
    }
    bundle_path = g_path_get_dirname(executable_path);
    g_free(executable_path);
    return bundle_path;
}

gchar *gtkosx_application_get_resource_path(void)
{
    const gchar *resource_path = g_getenv("OHOS_RESOURCE_PATH");

    if (resource_path != NULL && *resource_path != '\0') {
        return g_strdup(resource_path);
    }
    return gtkosx_application_get_bundle_path();
}

gchar *gtkosx_application_get_executable_path(void)
{
    gchar *path = g_file_read_link("/proc/self/exe", NULL);
    if (path == NULL) {
        const gchar *name = g_get_prgname();
        path = g_strdup(name != NULL ? name : "");
    }
    return path;
}

gchar *gtkosx_application_get_bundle_id(void)
{
    const gchar *bundle_id = g_getenv("OHOS_BUNDLE_NAME");

    if (bundle_id == NULL || *bundle_id == '\0') {
        bundle_id = g_get_application_name();
    }
    if (bundle_id == NULL || *bundle_id == '\0') {
        bundle_id = g_get_prgname();
    }
    return bundle_id != NULL ? g_strdup(bundle_id) : NULL;
}

gchar *gtkosx_application_get_bundle_info(const gchar *key)
{
    const gchar *value = NULL;

    g_return_val_if_fail(key != NULL, NULL);
    if (g_str_equal(key, "CFBundleIdentifier")) {
        return gtkosx_application_get_bundle_id();
    }
    if (g_str_equal(key, "CFBundleName")) {
        value = g_get_application_name();
    } else if (g_str_equal(key, "CFBundleVersion")) {
        value = g_getenv("OHOS_APP_VERSION_CODE");
    } else if (g_str_equal(key, "CFBundleShortVersionString")) {
        value = g_getenv("OHOS_APP_VERSION_NAME");
    } else if (g_str_equal(key, "CFBundleExecutable")) {
        gchar *path = gtkosx_application_get_executable_path();
        gchar *name = path != NULL ? g_path_get_basename(path) : NULL;
        g_free(path);
        return name;
    }

    if (value != NULL && *value != '\0') {
        return g_strdup(value);
    }
    return NULL;
}
