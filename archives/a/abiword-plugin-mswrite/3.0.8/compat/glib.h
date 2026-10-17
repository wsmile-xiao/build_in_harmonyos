/* compat/glib.h — OHOS minimal glib type shim
 * Provides the tiny subset of GLib types/macros used by the mswrite
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

/* Minimal GObject shim: the mswrite plugin calls g_object_ref/unref on the
 * GsfInput it stores; refcount is a plain int in this compile-time shim. */
typedef struct _GObject GObject;
#define G_OBJECT(o) ((GObject *)(o))

static inline GObject * g_object_ref (GObject * obj) { return obj; }
static inline void g_object_unref (GObject * /*obj*/) {}

/* case-insensitive ASCII comparison (GLib) */
static inline int g_ascii_strcasecmp (const char * s1, const char * s2)
{
	while (*s1 && *s2)
	{
		int c1 = *s1, c2 = *s2;
		if (c1 >= 'A' && c1 <= 'Z') c1 += 'a' - 'A';
		if (c2 >= 'A' && c2 <= 'Z') c2 += 'a' - 'A';
		if (c1 != c2)
			return c1 - c2;
		s1++;
		s2++;
	}
	return *s1 - *s2;
}

#endif /* COMPAT_GLIB_H */
