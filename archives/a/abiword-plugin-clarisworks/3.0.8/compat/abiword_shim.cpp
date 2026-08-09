/* compat/abiword_shim.cpp — OHOS minimal AbiWord/libgsf runtime shim
 *
 * Implementations backing the compat/ headers for the clarisworks plugin.
 * Self-contained; no dependency on the real AbiWord core or libgsf.
 */
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "ut_types.h"
#include "ut_debugmsg.h"
#include "ut_assert.h"
#include "ut_growbuf.h"
#include "ie_types.h"
#include "ie_imp.h"
#include "pd_Document.h"
#include "gsf/gsf-input.h"

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
	 * ClarisWorks importer emits (UT_UCSChar is a full codepoint). */
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
