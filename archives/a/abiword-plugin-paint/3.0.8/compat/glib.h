/* compat/glib.h — OHOS minimal GLib type/function shim
 *
 * Provides the tiny subset of GLib types and functions used by the
 * AbiPaint plugin (AbiGeneric.h/AbiPaint.cpp).  Do not install;
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
typedef gint32    gint;
typedef guint32   guint;
typedef void *    gpointer;
typedef size_t    gsize;   /* GLib: size_t 别名（无符号、指针宽度） */

#ifndef FALSE
#define FALSE 0
#endif
#ifndef TRUE
#define TRUE 1
#endif

/* GError — minimal (AbiPaint uses err->message / g_error_free) */
typedef struct _GError {
	gchar * message;
	gint    domain;
	gint    code;
} GError;

/* GSeekType values (GLib) */
#ifndef G_SEEK_SET
#define G_SEEK_SET 0
#define G_SEEK_CUR 1
#define G_SEEK_END 2
#endif

#define G_N_ELEMENTS(arr) (sizeof(arr) / sizeof((arr)[0]))

#ifdef __cplusplus
extern "C" {
#endif

void   g_free (gpointer mem);
void   g_warning (const char * format, ...);
void   g_error_free (GError * err);
void   g_usleep (unsigned long usec);
gint   g_file_open_tmp (const char * tmpl, gchar ** name_used, GError ** error);

#ifdef __cplusplus
}
#endif

#endif /* COMPAT_GLIB_H */
