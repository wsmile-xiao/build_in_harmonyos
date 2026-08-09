/* compat/gsf/gsf-input.h — OHOS minimal libgsf GsfInput shim
 *
 * The clarisworks plugin parses a ClarisWorks 5 (.cwk) file through the
 * libgsf GsfInput API (gsf_input_seek/read/tell).  libgsf is not published
 * for HarmonyOS, so this shim implements exactly that API surface over a
 * memory buffer.  Include path: -I$(top_srcdir)/compat so
 * <gsf/gsf-input.h> resolves here.
 */
#ifndef GSF_INPUT_H
#define GSF_INPUT_H

#include <stddef.h>
#include <string.h>
#include "glib.h"

typedef gint64 gsf_off_t;

typedef struct _GsfInput GsfInput;

struct _GsfInput {
	guint8 *   data;   /* owned copy of the buffer */
	gsf_off_t  size;
	gsf_off_t  pos;
};

/* compat helper: wrap a byte buffer (data is copied) */
GsfInput * gsf_input_new_from_memory (const void * data, size_t size);
void       gsf_input_free (GsfInput * input);

/* libgsf API used by the plugin */
gboolean            gsf_input_seek (GsfInput * input, gsf_off_t offset, int whence);
const guint8 *      gsf_input_read (GsfInput * input, size_t num_bytes, guint8 * buffer);
gsf_off_t           gsf_input_tell (GsfInput * input);

#endif /* GSF_INPUT_H */
