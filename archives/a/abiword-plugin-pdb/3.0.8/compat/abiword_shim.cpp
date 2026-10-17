/* compat/abiword_shim.cpp — OHOS minimal AbiWord/libgsf runtime shim
 *
 * Implementations backing the compat/ headers for the pdb plugin
 * (importer/exporter).  Self-contained; no dependency on the real
 * AbiWord core or libgsf.
 */
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

#include "ut_types.h"
#include "ut_debugmsg.h"
#include "ut_assert.h"
#include "ut_growbuf.h"
#include "ut_path.h"
#include "ie_types.h"
#include "ie_imp.h"
#include "ie_exp.h"
#include "ie_exp_Text.h"
#include "pd_Document.h"
#include "gsf/gsf-input.h"
#include "gsf/gsf-output.h"

/* ================================================================== */
/* debug output                                                       */
/* ================================================================== */

void _UT_OutputMessage (const char *s, ...)
{
	va_list args;
	va_start (args, s);
	vfprintf (stderr, s, args);
	va_end (args);
}

/* ================================================================== */
/* GLib / path helpers                                                */
/* ================================================================== */

int g_ascii_strcasecmp (const char * s1, const char * s2)
{
	if (!s1)
		return s2 ? -1 : 0;
	if (!s2)
		return 1;
	return strcasecmp (s1, s2);
}

const char * UT_basename (const char * pPath)
{
	if (!pPath)
		return "";
	const char * base = pPath;
	for (const char * p = pPath; *p; p++) {
		if (*p == '/' || *p == '\\')
			base = p + 1;
	}
	return base;
}

/* ================================================================== */
/* UT_GrowBuf                                                         */
/* ================================================================== */

UT_GrowBuf::UT_GrowBuf (UT_uint32 /*iChunk*/)
{
}

UT_GrowBuf::~UT_GrowBuf ()
{
}

bool UT_GrowBuf::ins (UT_uint32 position, const UT_GrowBufElement * pValue, UT_uint32 length)
{
	if (position > m_buf.size ())
		return false;
	if (!pValue && length > 0)
		return false;
	m_buf.insert (m_buf.begin () + position, pValue, pValue + length);
	return true;
}

void UT_GrowBuf::truncate (UT_uint32 position)
{
	if (position < m_buf.size ())
		m_buf.resize (position);
}

UT_uint32 UT_GrowBuf::getLength (void) const
{
	return (UT_uint32)m_buf.size ();
}

UT_GrowBufElement * UT_GrowBuf::getPointer (UT_uint32 position) const
{
	if (position >= m_buf.size ())
		return 0;
	return const_cast<UT_GrowBufElement *> (&m_buf[position]);
}

/* ================================================================== */
/* PD_Document stub                                                   */
/* ================================================================== */

PD_Document::PD_Document ()
	: m_spanCount (0)
{
}

PD_Document::~PD_Document ()
{
}

bool PD_Document::appendStrux (PTStruxType type, const char ** /*attributes*/)
{
	m_struxes.push_back (type);
	return true;
}

bool PD_Document::appendSpan (const UT_UCSChar * text, UT_uint32 length)
{
	if (!text)
		return false;
	m_text.insert (m_text.end (), text, text + length);
	m_spanCount++;
	return true;
}

std::string PD_Document::getExtractedText () const
{
	/* Only the low byte matters for the ASCII/Latin-1 data the
	 * PalmDoc importer emits (UT_UCSChar is a full codepoint). */
	std::string out;
	out.reserve (m_text.size ());
	for (size_t i = 0; i < m_text.size (); i++)
		out.push_back (static_cast<char> (m_text[i] & 0xFF));
	return out;
}

/* ================================================================== */
/* GsfInput memory shim                                               */
/* ================================================================== */

GsfInput * gsf_input_new_from_memory (const void * data, size_t size)
{
	GsfInput * in = (GsfInput *)calloc (1, sizeof (GsfInput));
	if (!in)
		return 0;
	in->data = (guint8 *)malloc (size ? size : 1);
	if (!in->data) {
		free (in);
		return 0;
	}
	if (size && !data) {
		/* size > 0 但 data 为空：释放已分配资源，避免 memcpy 崩溃 */
		free (in->data);
		free (in);
		return 0;
	}
	if (size)
		memcpy (in->data, data, size);
	in->size = (gsf_off_t)size;
	in->pos  = 0;
	return in;
}

void gsf_input_free (GsfInput * input)
{
	if (!input)
		return;
	free (input->data);
	free (input);
}

gboolean gsf_input_seek (GsfInput * input, gsf_off_t offset, int whence)
{
	if (!input)
		return FALSE;

	gsf_off_t base;
	if (whence == G_SEEK_SET)
		base = 0;
	else if (whence == G_SEEK_CUR)
		base = input->pos;
	else if (whence == G_SEEK_END)
		base = input->size;
	else
		return FALSE;

	gsf_off_t np = base + offset;
	if (np < 0 || np > input->size)
		return FALSE;
	input->pos = np;
	return TRUE;
}

const guint8 * gsf_input_read (GsfInput * input, size_t num_bytes, guint8 * buffer)
{
	if (!input || !buffer || num_bytes == 0)
		return 0;
	if (input->pos + (gsf_off_t)num_bytes > input->size)
		return 0;   /* EOF / short read */
	memcpy (buffer, input->data + input->pos, num_bytes);
	input->pos += (gsf_off_t)num_bytes;
	return buffer;
}

gsf_off_t gsf_input_tell (GsfInput * input)
{
	return input ? input->pos : 0;
}

/* ================================================================== */
/* GsfOutput memory shim (growable buffer)                            */
/* ================================================================== */

GsfOutput * gsf_output_new_from_memory (void)
{
	GsfOutput * out = (GsfOutput *)calloc (1, sizeof (GsfOutput));
	if (!out)
		return 0;
	out->data = (guint8 *)malloc (64);
	if (!out->data) {
		free (out);
		return 0;
	}
	out->size = 0;
	out->pos  = 0;
	return out;
}

void gsf_output_free (GsfOutput * output)
{
	if (!output)
		return;
	free (output->data);
	free (output);
}

gsf_off_t gsf_output_tell (GsfOutput * output)
{
	return output ? output->pos : 0;
}

gboolean gsf_output_seek (GsfOutput * output, gsf_off_t offset, int whence)
{
	if (!output)
		return FALSE;

	gsf_off_t base;
	if (whence == G_SEEK_SET)
		base = 0;
	else if (whence == G_SEEK_CUR)
		base = output->pos;
	else if (whence == G_SEEK_END)
		base = output->size;
	else
		return FALSE;

	gsf_off_t np = base + offset;
	if (np < 0)
		return FALSE;
	/* seeking past the current end is allowed; the buffer is zero-fill
	 * grown on the next write */
	output->pos = np;
	return TRUE;
}

gsf_off_t gsf_output_write (GsfOutput * output, size_t num_bytes, const guint8 * buffer)
{
	if (!output || !buffer || num_bytes == 0)
		return 0;

	gsf_off_t end = output->pos + (gsf_off_t)num_bytes;
	if (end > output->size) {
		/* grow the buffer (at least 1.5x, or enough for the write) */
		gsf_off_t need = end > output->size * 2 ? end : (output->size * 2) + 32;
		if (need < 64)
			need = 64;
		guint8 * nd = (guint8 *)realloc (output->data, (size_t)need);
		if (!nd)
			return 0;
		output->data = nd;
		if (output->pos > output->size)
			memset (output->data + output->size, 0,
			        (size_t)(output->pos - output->size));
	}

	memcpy (output->data + output->pos, buffer, num_bytes);
	output->pos += (gsf_off_t)num_bytes;
	if (output->pos > output->size)
		output->size = output->pos;
	return (gsf_off_t)num_bytes;
}

const guint8 * gsf_output_get_data (const GsfOutput * output)
{
	return output ? output->data : 0;
}

gsf_off_t gsf_output_get_size (const GsfOutput * output)
{
	return output ? output->size : 0;
}

/* ================================================================== */
/* Importer framework                                                 */
/* ================================================================== */

static std::vector<IE_ImpSniffer *> & importer_registry ()
{
	static std::vector<IE_ImpSniffer *> reg;
	return reg;
}

IE_ImpSniffer::IE_ImpSniffer (const char * name)
	: m_name (name ? name : ""), m_type (IEFT_Unknown)
{
}

IE_ImpSniffer::~IE_ImpSniffer ()
{
}

UT_Confidence_t IE_ImpSniffer::recognizeContents (const char * /*szBuf*/, UT_uint32 /*iNumbytes*/)
{
	return UT_CONFIDENCE_ZILCH;
}

UT_Confidence_t IE_ImpSniffer::recognizeContents (GsfInput * /*input*/)
{
	return UT_CONFIDENCE_ZILCH;
}

void IE_Imp::registerImporter (IE_ImpSniffer * sniffer)
{
	if (!sniffer)
		return;
	std::vector<IE_ImpSniffer *> & reg = importer_registry ();
	for (size_t i = 0; i < reg.size (); i++)
		if (reg[i] == sniffer)
			return;
	reg.push_back (sniffer);
}

void IE_Imp::unregisterImporter (IE_ImpSniffer * sniffer)
{
	std::vector<IE_ImpSniffer *> & reg = importer_registry ();
	for (size_t i = 0; i < reg.size (); i++) {
		if (reg[i] == sniffer) {
			reg.erase (reg.begin () + i);
			return;
		}
	}
}

std::vector<IE_ImpSniffer *> & IE_Imp::registeredImporters ()
{
	return importer_registry ();
}

IE_Imp::IE_Imp (PD_Document * pDocument)
	: m_pDocument (pDocument)
{
}

IE_Imp::~IE_Imp ()
{
}

bool IE_Imp::appendStrux (PTStruxType pts, const char ** attributes)
{
	if (!m_pDocument)
		return false;
	return m_pDocument->appendStrux (pts, attributes);
}

bool IE_Imp::appendSpan (const UT_UCSChar * p, UT_uint32 length)
{
	if (!m_pDocument)
		return false;
	return m_pDocument->appendSpan (p, length);
}

UT_Error IE_Imp::importFile (GsfInput * input)
{
	if (!input)
		return UT_IE_COULDNOTOPEN;
	return _loadFile (input);
}

/* ================================================================== */
/* Exporter framework                                                 */
/* ================================================================== */

static std::vector<IE_ExpSniffer *> & exporter_registry ()
{
	static std::vector<IE_ExpSniffer *> reg;
	return reg;
}

IE_ExpSniffer::IE_ExpSniffer (const char * name)
	: m_name (name ? name : ""), m_type (IEFT_Unknown)
{
}

IE_ExpSniffer::~IE_ExpSniffer ()
{
}

void IE_Exp::registerExporter (IE_ExpSniffer * sniffer)
{
	if (!sniffer)
		return;
	std::vector<IE_ExpSniffer *> & reg = exporter_registry ();
	for (size_t i = 0; i < reg.size (); i++)
		if (reg[i] == sniffer)
			return;
	reg.push_back (sniffer);
}

void IE_Exp::unregisterExporter (IE_ExpSniffer * sniffer)
{
	std::vector<IE_ExpSniffer *> & reg = exporter_registry ();
	for (size_t i = 0; i < reg.size (); i++) {
		if (reg[i] == sniffer) {
			reg.erase (reg.begin () + i);
			return;
		}
	}
}

std::vector<IE_ExpSniffer *> & IE_Exp::registeredExporters ()
{
	return exporter_registry ();
}

IE_Exp::IE_Exp (PD_Document * pDocument)
	: m_pDocument (pDocument), m_fp (0)
{
}

IE_Exp::~IE_Exp ()
{
}

void IE_Exp::setOutput (GsfOutput * fp, const char * fileName)
{
	m_fp = fp;
	m_fileName = fileName ? fileName : "";
}

UT_Error IE_Exp::writeDocument ()
{
	return _writeDocument ();
}

/* ---- IE_Exp_Text ---- */

IE_Exp_Text::IE_Exp_Text (PD_Document * pDocument)
	: IE_Exp (pDocument)
{
}

IE_Exp_Text::~IE_Exp_Text ()
{
}

UT_uint32 IE_Exp_Text::_writeBytes (const UT_Byte * pBytes, UT_uint32 length)
{
	/* The pdb exporter buffers text internally and only needs the raw
	 * bytes; the default base implementation just forwards to getFp(). */
	if (!pBytes || !length)
		return 0;
	GsfOutput * fp = getFp ();
	if (!fp)
		return 0;   /* no output stream attached: report failure instead of faking success */
	gsf_off_t written = gsf_output_write (fp, length, pBytes);
	if (written != (gsf_off_t)length)
		return 0;   /* short write / realloc failure: propagate so _writeDocument() can fail */
	return length;
}

bool IE_Exp_Text::_writeBytes (const UT_Byte * sz)
{
	if (!sz)
		return false;
	return _writeBytes (sz, (UT_uint32)strlen (reinterpret_cast<const char *> (sz)))
		== (UT_uint32)strlen (reinterpret_cast<const char *> (sz));
}

UT_Error IE_Exp_Text::_writeDocument ()
{
	/* Stream the text recorded by the PD_Document shim (low byte of each
	 * UCS char) through the exporter's _writeBytes hooks.  The pdb
	 * exporter overrides _writeBytes to buffer + PalmDoc-compress. */
	if (!getDoc ())
		return UT_ERROR;
	std::string text = getDoc ()->getExtractedText ();
	if (!text.empty ()) {
		UT_uint32 written = _writeBytes (reinterpret_cast<const UT_Byte *> (text.data ()),
		                                (UT_uint32)text.size ());
		if (written != (UT_uint32)text.size ())
			return UT_IE_IMPORTERROR;
	}
	return UT_OK;
}
