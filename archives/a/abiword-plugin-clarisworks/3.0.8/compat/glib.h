/* compat/glib.h — OHOS minimal glib type shim
 * Provides the tiny subset of GLib types/macros used by the clarisworks
 * plugin source.  Do not install; compile-time shim only.
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

/* GSeekType values (GLib) */
#ifndef G_SEEK_SET
#define G_SEEK_SET 0
#define G_SEEK_CUR 1
#define G_SEEK_END 2
#endif

#endif /* COMPAT_GLIB_H */
