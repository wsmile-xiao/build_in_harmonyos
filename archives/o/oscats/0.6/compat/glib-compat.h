/* compat/glib-compat.h -- glib 2.8x compatibility shim for oscats 0.6 (2011)
 *
 * GLib 2.80 removed the classic G_MIN.../G_MAX... constant family from
 * glib/gtypes.h (they had been deprecated in favour of the C99
 * <limits.h>/<float.h> constants).  oscats 0.6 uses them for GObject
 * property ranges (1, G_MAXUINT, ...) and numeric sentinels
 * (-G_MAXDOUBLE, G_MINDOUBLE, G_MAXDOUBLE).
 *
 * This header is force-injected with `-include` by the recipe so the
 * definitions exist for every translation unit (glib's own headers do not
 * pull in <limits.h>/<float.h>).  Each definition is guarded with
 * #ifndef so any macro glib still provides wins.
 */
#ifndef OSCATS_GLIB_COMPAT_H
#define OSCATS_GLIB_COMPAT_H

#include <limits.h>
#include <float.h>

/* Signed integer limits */
#ifndef G_MINSHORT
#define G_MINSHORT  ((gshort) SHRT_MIN)
#endif
#ifndef G_MAXSHORT
#define G_MAXSHORT  ((gshort) SHRT_MAX)
#endif
#ifndef G_MININT
#define G_MININT    ((gint) INT_MIN)
#endif
#ifndef G_MAXINT
#define G_MAXINT    ((gint) INT_MAX)
#endif
#ifndef G_MINLONG
#define G_MINLONG   ((glong) LONG_MIN)
#endif
#ifndef G_MAXLONG
#define G_MAXLONG   ((glong) LONG_MAX)
#endif

/* Unsigned integer limits */
#ifndef G_MINUINT
#define G_MINUINT   ((guint) 0)
#endif
#ifndef G_MAXUINT
#define G_MAXUINT   ((guint) UINT_MAX)
#endif
#ifndef G_MINULONG
#define G_MINULONG  ((gulong) 0)
#endif
#ifndef G_MAXULONG
#define G_MAXULONG  ((gulong) ULONG_MAX)
#endif

/* Floating point limits */
#ifndef G_MINFLOAT
#define G_MINFLOAT  ((gfloat) FLT_MIN)
#endif
#ifndef G_MAXFLOAT
#define G_MAXFLOAT  ((gfloat) FLT_MAX)
#endif
#ifndef G_MINDOUBLE
#define G_MINDOUBLE ((gdouble) DBL_MIN)
#endif
#ifndef G_MAXDOUBLE
#define G_MAXDOUBLE ((gdouble) DBL_MAX)
#endif

#endif /* OSCATS_GLIB_COMPAT_H */
