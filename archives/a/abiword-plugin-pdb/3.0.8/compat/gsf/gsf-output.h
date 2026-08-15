/* compat/gsf/gsf-output.h — OHOS minimal libgsf GsfOutput shim
 *
 * The pdb exporter writes a PalmDoc (.pdb) database through the libgsf
 * GsfOutput API (gsf_output_write/seek/tell).  libgsf is not published
 * for HarmonyOS, so this shim implements exactly that API surface over a
 * growable in-memory buffer.  Include path: -I$(top_srcdir)/compat so
 * <gsf/gsf-output.h> resolves here.
 */
#ifndef GSF_OUTPUT_H
#define GSF_OUTPUT_H

#include <stddef.h>
#include <string.h>
#include "glib.h"

typedef struct _GsfOutput GsfOutput;

struct _GsfOutput {
	guint8 *   data;   /* owned growable buffer */
	gsf_off_t  size;   /* number of bytes written so far */
	gsf_off_t  pos;    /* current position */
};

/* compat helper: create an empty in-memory output stream */
GsfOutput * gsf_output_new_from_memory (void);
void        gsf_output_free (GsfOutput * output);

/* libgsf API used by the plugin */
gboolean            gsf_output_seek (GsfOutput * output, gsf_off_t offset, int whence);
gsf_off_t           gsf_output_tell (GsfOutput * output);
gsf_off_t           gsf_output_write (GsfOutput * output, size_t num_bytes, const guint8 * buffer);

/* compat test hooks */
const guint8 * gsf_output_get_data (const GsfOutput * output);
gsf_off_t      gsf_output_get_size (const GsfOutput * output);

#endif /* GSF_OUTPUT_H */
