/* Minimal gettext/libintl API shim for OHOS PC.
 *
 * GLib's <glib/gi18n.h> unconditionally #includes <libintl.h>, but the
 * OHOS PC toolchain ships neither GNU gettext nor a libintl header.
 * Since the conan glib/2.88 package is built without NLS (translations
 * are not packaged on OHOS), a pass-through implementation is correct:
 * every message is used verbatim (English upstream strings).
 */
#ifndef OHC_LIBINTL_SHIM_H
#define OHC_LIBINTL_SHIM_H

#include <locale.h>

#ifndef LC_MESSAGES
#define LC_MESSAGES 1729
#endif

#define gettext(String)           ((const char *)(String))
#define dgettext(Domain, String)  ((const char *)(String))
#define dcgettext(Domain, String, Category) ((const char *)(String))
#define ngettext(String1, String2, N)       (((N) == 1) ? (const char *)(String1) : (const char *)(String2))
#define dngettext(Domain, String1, String2, N) (((N) == 1) ? (const char *)(String1) : (const char *)(String2))
#define textdomain(Domain)        ((const char *)(Domain))
#define bindtextdomain(Domain, Directory) ((const char *)(Domain))
#define bind_textdomain_codeset(Domain, Charset) ((const char *)(Domain))

#endif /* OHC_LIBINTL_SHIM_H */
