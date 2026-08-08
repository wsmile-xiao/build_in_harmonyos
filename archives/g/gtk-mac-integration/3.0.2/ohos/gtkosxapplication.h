/* HarmonyOS compatibility API for gtk-mac-integration 3.0.2. */
#ifndef GTKOSX_APPLICATION_H
#define GTKOSX_APPLICATION_H

#include <glib-object.h>

G_BEGIN_DECLS

typedef struct _GtkWidget GtkWidget;
typedef struct _GtkMenuShell GtkMenuShell;
typedef struct _GtkMenuItem GtkMenuItem;
typedef struct _GdkPixbuf GdkPixbuf;
typedef struct _GtkosxApplication GtkosxApplication;
typedef struct _GtkosxApplicationClass GtkosxApplicationClass;

#define GTKOSX_TYPE_APPLICATION (gtkosx_application_get_type())
#define GTKOSX_APPLICATION(obj) \
    (G_TYPE_CHECK_INSTANCE_CAST((obj), GTKOSX_TYPE_APPLICATION, GtkosxApplication))
#define GTKOSX_IS_APPLICATION(obj) \
    (G_TYPE_CHECK_INSTANCE_TYPE((obj), GTKOSX_TYPE_APPLICATION))
#define GTKOSX_APPLICATION_CLASS(klass) \
    (G_TYPE_CHECK_CLASS_CAST((klass), GTKOSX_TYPE_APPLICATION, GtkosxApplicationClass))
#define GTKOSX_IS_APPLICATION_CLASS(klass) \
    (G_TYPE_CHECK_CLASS_TYPE((klass), GTKOSX_TYPE_APPLICATION))
#define GTKOSX_APPLICATION_GET_CLASS(obj) \
    (G_TYPE_INSTANCE_GET_CLASS((obj), GTKOSX_TYPE_APPLICATION, GtkosxApplicationClass))

typedef enum {
    GTKOSX_APPLICATION_ATTENTION_TYPE_CRITICAL_REQUEST = 0,
    GTKOSX_APPLICATION_ATTENTION_TYPE_INFO_REQUEST = 1
} GtkosxApplicationAttentionType;

GType gtkosx_application_get_type(void);
GtkosxApplication *gtkosx_application_get(void);
void gtkosx_application_ready(GtkosxApplication *self);
void gtkosx_application_set_use_quartz_accelerators(
    GtkosxApplication *self, gboolean enabled
);
gboolean gtkosx_application_use_quartz_accelerators(GtkosxApplication *self);
void gtkosx_application_set_menu_bar(
    GtkosxApplication *self, GtkMenuShell *menu_shell
);
void gtkosx_application_sync_menubar(GtkosxApplication *self);
void gtkosx_application_insert_app_menu_item(
    GtkosxApplication *self, GtkWidget *menu_item, gint index
);
void gtkosx_application_set_about_item(
    GtkosxApplication *self, GtkWidget *item
);
void gtkosx_application_set_window_menu(
    GtkosxApplication *self, GtkMenuItem *menu_item
);
void gtkosx_application_set_help_menu(
    GtkosxApplication *self, GtkMenuItem *menu_item
);
void gtkosx_application_set_dock_menu(
    GtkosxApplication *self, GtkMenuShell *menu_shell
);
void gtkosx_application_set_dock_icon_pixbuf(
    GtkosxApplication *self, GdkPixbuf *pixbuf
);
void gtkosx_application_set_dock_icon_resource(
    GtkosxApplication *self,
    const gchar *name,
    const gchar *type,
    const gchar *subdir
);
gint gtkosx_application_attention_request(
    GtkosxApplication *self, GtkosxApplicationAttentionType type
);
void gtkosx_application_cancel_attention_request(
    GtkosxApplication *self, gint id
);
gchar *gtkosx_application_get_bundle_path(void);
gchar *gtkosx_application_get_resource_path(void);
gchar *gtkosx_application_get_executable_path(void);
gchar *gtkosx_application_get_bundle_id(void);
gchar *gtkosx_application_get_bundle_info(const gchar *key);

G_END_DECLS

#endif
