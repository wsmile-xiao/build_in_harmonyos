/* compat/glib.h — OHOS minimal glib type shim
 * Provides the tiny subset of GLib types/macros used by the pdb plugin
 * source (and the sibling clarisworks/bmp plugins).  Do not install;
 * compile-time shim only.
 */
#ifndef COMPAT_GLIB_H
#define COMPAT_GLIB_H

#include <stdint.h>
#include <stddef.h>

typedef uint8_t   guint8;
typedef int8_t    gint8;
typedef uint16_t  guint16;
typedef int16_t   gint16;
typedef uint32_t  guint32;
typedef int32_t   gint32;
typedef uint64_t  guint64;
typedef int64_t   gint64;
typedef char      gchar;
typedef int       gboolean;
typedef guint32   gunichar;

#ifndef FALSE
#define FALSE 0
#endif
#ifndef TRUE
#define TRUE 1
#endif

/* gsf_off_t shared by the GsfInput / GsfOutput shims */
#ifndef GSF_OFF_T_DEFINED
#define GSF_OFF_T_DEFINED
typedef gint64 gsf_off_t;
#endif

/* GSeekType values (GLib) */
#ifndef G_SEEK_SET
#define G_SEEK_SET 0
#define G_SEEK_CUR 1
#define G_SEEK_END 2
#endif

/* ------------------------------------------------------------------ */
/* GObject shim (subset used by the pdb plugin)                        */
/* ------------------------------------------------------------------ */
/* The pdb importer refs/unrefs its GsfInput through the GLib object
 * API.  Memory is owned by the caller in the shim, so g_object_ref is
 * an identity and g_object_unref is a no-op. */
typedef struct _GObject GObject;

#define G_OBJECT(o) ((GObject *)(o))

static inline GObject * g_object_ref (GObject * o) { return o; }
static inline void g_object_unref (GObject * o)    { (void)o; }

/* Case-insensitive ASCII string compare (GLib g_ascii_strcasecmp). */
int g_ascii_strcasecmp (const char * s1, const char * s2);

#endif /* COMPAT_GLIB_H */
