/* compat/abiword_shim.cpp — OHOS minimal AbiWord runtime shim
 *
 * Implementations backing the compat/ headers for the abiword-plugin-opml
 * module.  Self-contained; no dependency on the real AbiWord core or
 * libxml2.  Includes a minimal SAX-style XML parser driving the
 * IE_Imp_XML::startElement / endElement / charData callbacks.
 */
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <string>
#include <vector>

#include "ut_types.h"
#include "ut_debugmsg.h"
#include "ut_assert.h"
#include "ut_growbuf.h"
#include "ut_string_class.h"
#include "ie_types.h"
#include "ie_imp.h"
#include "ie_imp_XML.h"
#include "pd_Document.h"
#include "fl_AutoNum.h"
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
/* GLib helpers                                                       */
/* ================================================================== */

gchar * g_strdup (const char * s)
{
	if (!s)
		return NULL;
	size_t n = strlen (s) + 1;
	gchar * p = (gchar *)malloc (n);
	if (p)
		memcpy (p, s, n);
	return p;
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
/* UT_UCS4String (UTF-8 → UCS4)                                       */
/* ================================================================== */

static void _utf8_to_ucs4 (const char * s, size_t len, std::vector<UT_UCS4Char> & out)
{
	size_t i = 0;
	while (i < len) {
		unsigned char c = (unsigned char)s[i];
		UT_UCS4Char cp;
		if (c < 0x80) {
			cp = c; i += 1;
		} else if ((c & 0xE0) == 0xC0 && i + 1 < len &&
		           ((unsigned char)s[i+1] & 0xC0) == 0x80) {
			cp = ((UT_UCS4Char)(c & 0x1F) << 6) | (unsigned char)(s[i+1] & 0x3F);
			i += 2;
		} else if ((c & 0xF0) == 0xE0 && i + 2 < len &&
		           ((unsigned char)s[i+1] & 0xC0) == 0x80 &&
		           ((unsigned char)s[i+2] & 0xC0) == 0x80) {
			cp = ((UT_UCS4Char)(c & 0x0F) << 12) |
			     ((UT_UCS4Char)(s[i+1] & 0x3F) << 6) |
			     (UT_UCS4Char)(s[i+2] & 0x3F);
			i += 3;
		} else if ((c & 0xF8) == 0xF0 && i + 3 < len &&
		           ((unsigned char)s[i+1] & 0xC0) == 0x80 &&
		           ((unsigned char)s[i+2] & 0xC0) == 0x80 &&
		           ((unsigned char)s[i+3] & 0xC0) == 0x80) {
			cp = ((UT_UCS4Char)(c & 0x07) << 18) |
			     ((UT_UCS4Char)(s[i+1] & 0x3F) << 12) |
			     ((UT_UCS4Char)(s[i+2] & 0x3F) << 6) |
			     (UT_UCS4Char)(s[i+3] & 0x3F);
			i += 4;
		} else {
			cp = c; i += 1;
		}
		out.push_back (cp);
	}
}

UT_UCS4String::UT_UCS4String (const UT_UCS4Char * sz, size_t n)
{
	if (!sz)
		return;
	if (n == 0) {
		while (*sz)
			m_str.push_back (*sz++);
	} else {
		m_str.assign (sz, sz + n);
	}
}

UT_UCS4String::UT_UCS4String (const char * utf8_str, size_t bytelength)
{
	if (!utf8_str)
		return;
	size_t len = bytelength ? bytelength : strlen (utf8_str);
	_utf8_to_ucs4 (utf8_str, len, m_str);
}

UT_UCS4String::UT_UCS4String (const std::string & str)
{
	_utf8_to_ucs4 (str.data (), str.size (), m_str);
}

/* ================================================================== */
/* fl_AutoNum                                                         */
/* ================================================================== */

fl_AutoNum::fl_AutoNum (UT_uint32 id, UT_uint32 parent_id, FL_ListType lType,
                        UT_uint32 /*start*/, const gchar * /*lDelim*/,
                        const gchar * /*lDecimal*/, PD_Document * /*pDoc*/,
                        void * /*pView*/)
	: m_iID (id), m_iParentID (parent_id), m_List_Type (lType), m_iLevel (0)
{
}

fl_AutoNum::~fl_AutoNum ()
{
}

/* ================================================================== */
/* PD_Document stub                                                   */
/* ================================================================== */

PD_Document::PD_Document ()
	: m_spanCount (0), m_fmtDepth (0)
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

bool PD_Document::appendObject (PTObjectType type, const char ** /*attributes*/)
{
	m_objects.push_back (type);
	return true;
}

bool PD_Document::appendFmt (const char ** /*attributes*/)
{
	m_fmtDepth++;
	return true;
}

void PD_Document::popInlineFmt ()
{
	if (m_fmtDepth > 0)
		m_fmtDepth--;
}

void PD_Document::addList (fl_AutoNumPtr an)
{
	if (an)
		m_lists.push_back (an);
}

void PD_Document::setMetaDataProp (const char * key, const char * value)
{
	if (!key)
		return;
	m_metadata.push_back (std::make_pair (std::string (key),
	                                      value ? std::string (value) : std::string ()));
}

const char * PD_Document::getMetaDataProp (const char * key) const
{
	if (!key)
		return NULL;
	for (size_t i = 0; i < m_metadata.size (); i++) {
		if (m_metadata[i].first == key)
			return m_metadata[i].second.c_str ();
	}
	return NULL;
}

UT_uint32 PD_Document::countObjects (PTObjectType t) const
{
	UT_uint32 n = 0;
	for (size_t i = 0; i < m_objects.size (); i++)
		if (m_objects[i] == t)
			n++;
	return n;
}

std::string PD_Document::getExtractedText () const
{
	/* Only the low byte matters for the ASCII/Latin-1 data the OPML
	 * importer emits (UT_UCSChar is a full codepoint). */
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

	/* compute np = base + offset without signed overflow (offset may be
	 * as large as G_MAXINT64 / G_MININT64) */
	gsf_off_t np;
	if (offset >= 0) {
		guint64 sum = (guint64)base + (guint64)offset;
		if (sum > (guint64)input->size)
			return FALSE;
		np = (gsf_off_t)sum;
	} else {
		guint64 abs_off = (guint64)(-(offset + 1)) + 1;   /* safe for G_MININT64 */
		if ((guint64)base < abs_off)
			return FALSE;
		np = (gsf_off_t)((guint64)base - abs_off);
	}
	input->pos = np;
	return TRUE;
}

const guint8 * gsf_input_read (GsfInput * input, size_t num_bytes, guint8 * buffer)
{
	if (!input)
		return 0;
	if (input->pos + (gsf_off_t)num_bytes > input->size)
		return 0;   /* EOF / short read */
	const guint8 * ret;
	if (buffer) {
		memcpy (buffer, input->data + input->pos, num_bytes);
		ret = buffer;
	} else {
		/* NULL buffer: return a pointer into the internal buffer
		 * (libgsf semantics used by IE_Imp_XML::_loadFile) */
		ret = input->data + input->pos;
	}
	input->pos += (gsf_off_t)num_bytes;
	return ret;
}

gsf_off_t gsf_input_tell (GsfInput * input)
{
	return input ? input->pos : 0;
}

gsf_off_t gsf_input_size (GsfInput * input)
{
	return input ? input->size : 0;
}

const char * gsf_input_name (GsfInput * /*input*/)
{
	return "memory";
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

bool IE_Imp::appendObject (PTObjectType pto, const char ** attribs, const char ** /*props*/)
{
	if (!m_pDocument)
		return false;
	return m_pDocument->appendObject (pto, attribs);
}

bool IE_Imp::appendFmt (const char ** attributes)
{
	if (!m_pDocument)
		return false;
	return m_pDocument->appendFmt (attributes);
}

void IE_Imp::_popInlineFmt (void)
{
	if (m_pDocument)
		m_pDocument->popInlineFmt ();
}

UT_Error IE_Imp::importFile (GsfInput * input)
{
	if (!input)
		return UT_IE_COULDNOTOPEN;
	return _loadFile (input);
}

/* ================================================================== */
/* IE_Imp_XML — minimal XML importer base                             */
/* ================================================================== */

IE_Imp_XML::IE_Imp_XML (PD_Document * pDocument, bool whiteSignificant)
	: IE_Imp (pDocument),
	  m_error (UT_OK),
	  m_parseState (_PS_Init),
	  m_bWhiteSignificant (whiteSignificant),
	  m_iInlineFmtDepth (0)
{
}

IE_Imp_XML::~IE_Imp_XML ()
{
}

void IE_Imp_XML::startElement (const gchar * /*name*/, const gchar ** /*atts*/)
{
	UT_DEBUGMSG (("you must override virtual method IE_Imp_XML::startElement\n"));
}

void IE_Imp_XML::endElement (const gchar * /*name*/)
{
	UT_DEBUGMSG (("you must override virtual method IE_Imp_XML::endElement\n"));
}

void IE_Imp_XML::charData (const gchar * /*buffer*/, int /*length*/)
{
}

int IE_Imp_XML::_mapNameToToken (const char * name, xmlToIdMapping * idlist, int len)
{
	if (!name || !idlist)
		return -1;
	for (int i = 0; i < len; i++) {
		if (idlist[i].m_name && strcmp (idlist[i].m_name, name) == 0)
			return idlist[i].m_type;
	}
	return -1;
}

const gchar * IE_Imp_XML::_getXMLPropValue (const gchar * name, const gchar ** atts)
{
	if (!name || !atts)
		return NULL;
	for (int i = 0; atts[i] != NULL; i += 2) {
		if (atts[i] && strcmp (atts[i], name) == 0)
			return atts[i + 1];
	}
	return NULL;
}

void IE_Imp_XML::_pushInlineFmt (const gchar ** /*atts*/)
{
	m_iInlineFmtDepth++;
}

void IE_Imp_XML::_popInlineFmt (void)
{
	if (m_iInlineFmtDepth > 0)
		m_iInlineFmtDepth--;
}

/* ================================================================== */
/* minimal SAX-style XML parser                                       */
/* ================================================================== */

static inline bool _is_space (char c)
{
	return (c == ' ' || c == '\t' || c == '\r' || c == '\n');
}

static size_t _find_str (const char * data, size_t len, size_t from,
                         const char * needle)
{
	size_t nl = strlen (needle);
	if (from + nl > len)
		return (size_t)-1;
	for (size_t i = from; i + nl <= len; i++) {
		if (memcmp (data + i, needle, nl) == 0)
			return i;
	}
	return (size_t)-1;
}

static size_t _find_char (const char * data, size_t len, size_t from, char c)
{
	for (size_t i = from; i < len; i++)
		if (data[i] == c)
			return i;
	return (size_t)-1;
}

/* find the end of a <!DOCTYPE ...> declaration, honouring quotes and an
 * internal subset ([ ... ]) */
static size_t _find_doctype_end (const char * data, size_t len, size_t from)
{
	size_t i = from;
	int in_quote = 0;
	int in_subset = 0;
	while (i < len) {
		char c = data[i];
		if (in_quote) {
			if (c == in_quote)
				in_quote = 0;
		} else if (c == '"' || c == '\'') {
			in_quote = c;
		} else if (c == '[') {
			in_subset++;
		} else if (c == ']') {
			if (in_subset > 0)
				in_subset--;
		} else if (c == '>' && in_subset == 0) {
			return i;
		}
		i++;
	}
	return (size_t)-1;
}

static std::string _decode_entities (const char * s, size_t len)
{
	std::string out;
	size_t i = 0;
	while (i < len) {
		if (s[i] == '&') {
			size_t semi = i + 1;
			while (semi < len && s[semi] != ';' && (semi - i) <= 10)
				semi++;
			if (semi < len && s[semi] == ';') {
				std::string ent (s + i + 1, semi - i - 1);
				if (ent == "amp")      { out.push_back ('&'); i = semi + 1; continue; }
				if (ent == "lt")       { out.push_back ('<'); i = semi + 1; continue; }
				if (ent == "gt")       { out.push_back ('>'); i = semi + 1; continue; }
				if (ent == "quot")     { out.push_back ('"'); i = semi + 1; continue; }
				if (ent == "apos")     { out.push_back ('\''); i = semi + 1; continue; }
				if (ent.size () > 1 && ent[0] == '#') {
					unsigned long cp = 0;
					bool ok = true;
					if (ent[1] == 'x' || ent[1] == 'X') {
						for (size_t k = 2; k < ent.size (); k++) {
							char c = ent[k];
							cp *= 16;
							if (c >= '0' && c <= '9') cp += (unsigned long)(c - '0');
							else if (c >= 'a' && c <= 'f') cp += (unsigned long)(c - 'a' + 10);
							else if (c >= 'A' && c <= 'F') cp += (unsigned long)(c - 'A' + 10);
							else { ok = false; break; }
						}
					} else {
						for (size_t k = 1; k < ent.size (); k++) {
							char c = ent[k];
							if (c >= '0' && c <= '9') cp = cp * 10 + (unsigned long)(c - '0');
							else { ok = false; break; }
						}
					}
					if (ok) {
						/* encode as UTF-8 into out */
						if (cp < 0x80) {
							out.push_back ((char)cp);
						} else if (cp < 0x800) {
							out.push_back ((char)(0xC0 | (cp >> 6)));
							out.push_back ((char)(0x80 | (cp & 0x3F)));
						} else if (cp < 0x10000) {
							out.push_back ((char)(0xE0 | (cp >> 12)));
							out.push_back ((char)(0x80 | ((cp >> 6) & 0x3F)));
							out.push_back ((char)(0x80 | (cp & 0x3F)));
						} else {
							out.push_back ((char)(0xF0 | (cp >> 18)));
							out.push_back ((char)(0x80 | ((cp >> 12) & 0x3F)));
							out.push_back ((char)(0x80 | ((cp >> 6) & 0x3F)));
							out.push_back ((char)(0x80 | (cp & 0x3F)));
						}
						i = semi + 1;
						continue;
					}
				}
			}
			/* not a recognised entity: emit literally */
			out.push_back (s[i]);
			i++;
		} else {
			out.push_back (s[i]);
			i++;
		}
	}
	return out;
}

/* emit character data to the listener (entity-decoded) */
static void _emit_char_data (IE_Imp_XML * listener, const char * s, size_t len)
{
	if (!listener || len == 0)
		return;
	std::string decoded = _decode_entities (s, len);
	if (!decoded.empty ())
		listener->charData (decoded.c_str (), (int)decoded.size ());
}

/* emit character data verbatim — CDATA content must NOT be entity-decoded */
static void _emit_char_data_raw (IE_Imp_XML * listener, const char * s, size_t len)
{
	if (!listener || len == 0)
		return;
	listener->charData (s, (int)len);
}

/* entry point: parse an XML document and drive the listener callbacks */
UT_Error IE_Imp_XML::_parse_xml (IE_Imp_XML * listener, const char * data, size_t len)
{
	size_t pos = 0;
	size_t text_start = 0;

	while (pos < len) {
		if (data[pos] != '<') {
			pos++;
			continue;
		}

		/* flush pending character data */
		if (pos > text_start)
			_emit_char_data (listener, data + text_start, pos - text_start);

		if (pos + 1 >= len) {
			/* dangling '<' at EOF: leave text_start at pos so the
			 * trailing flush does not re-emit the text above */
			text_start = pos;
			break;
		}

		char c = data[pos + 1];

		if (c == '?') {
			/* processing instruction / XML declaration */
			size_t end = _find_str (data, len, pos, "?>");
			if (end == (size_t)-1)
				return UT_IE_BOGUSDOCUMENT;
			pos = end + 2;
		} else if (c == '!') {
			if (pos + 4 <= len && memcmp (data + pos, "<!--", 4) == 0) {
				size_t end = _find_str (data, len, pos, "-->");
				if (end == (size_t)-1)
					return UT_IE_BOGUSDOCUMENT;
				pos = end + 3;
			} else if (pos + 9 <= len && memcmp (data + pos, "<![CDATA[", 9) == 0) {
				size_t end = _find_str (data, len, pos, "]]>");
				if (end == (size_t)-1)
					return UT_IE_BOGUSDOCUMENT;
				_emit_char_data_raw (listener, data + pos + 9, end - (pos + 9));
				pos = end + 3;
			} else if (pos + 9 <= len && memcmp (data + pos, "<!DOCTYPE", 9) == 0) {
				size_t end = _find_doctype_end (data, len, pos);
				if (end == (size_t)-1)
					return UT_IE_BOGUSDOCUMENT;
				pos = end + 1;
			} else {
				size_t end = _find_char (data, len, pos, '>');
				if (end == (size_t)-1)
					return UT_IE_BOGUSDOCUMENT;
				pos = end + 1;
			}
		} else if (c == '/') {
			/* end tag </name> */
			size_t gt = _find_char (data, len, pos, '>');
			if (gt == (size_t)-1)
				return UT_IE_BOGUSDOCUMENT;
			size_t ns = pos + 2;
			size_t ne = gt;
			while (ns < ne && _is_space (data[ns]))
				ns++;
			while (ne > ns && _is_space (data[ne - 1]))
				ne--;
			std::string name (data + ns, ne - ns);
			listener->endElement (name.c_str ());
			if (listener->m_error != UT_OK)
				return listener->m_error;
			pos = gt + 1;
		} else {
			/* start tag <name attr="val" ...> or <name ... /> — scan for
			 * '>' honouring quoted attribute values */
			size_t gt = pos + 1;
			char in_quote = 0;
			while (gt < len) {
				char ch = data[gt];
				if (in_quote) {
					if (ch == in_quote)
						in_quote = 0;
				} else if (ch == '"' || ch == '\'') {
					in_quote = ch;
				} else if (ch == '>') {
					break;
				}
				gt++;
			}
			if (gt >= len)
				return UT_IE_BOGUSDOCUMENT;
			bool self_closing = (gt > pos + 1 && data[gt - 1] == '/');

			/* tag name */
			size_t name_end = pos + 1;
			while (name_end < gt && !_is_space (data[name_end]) &&
			       data[name_end] != '/' && data[name_end] != '>')
				name_end++;
			std::string name (data + pos + 1, name_end - (pos + 1));

			/* attributes */
			std::vector<std::string>  atts_store;
			std::vector<const char *> atts_vec;
			size_t ap = name_end;
			while (ap < gt) {
				while (ap < gt && (_is_space (data[ap]) || data[ap] == '/'))
					ap++;
				if (ap >= gt || data[ap] == '>')
					break;
				/* attribute name */
				size_t an = ap;
				while (ap < gt && !_is_space (data[ap]) && data[ap] != '=')
					ap++;
				std::string aname (data + an, ap - an);
				/* skip ws, expect '=' */
				while (ap < gt && _is_space (data[ap]))
					ap++;
				if (ap < gt && data[ap] == '=') {
					ap++;
					while (ap < gt && _is_space (data[ap]))
						ap++;
					if (ap < gt && (data[ap] == '"' || data[ap] == '\'')) {
						char q = data[ap];
						ap++;
						size_t vs = ap;
						while (ap < gt && data[ap] != q)
							ap++;
						std::string aval = _decode_entities (data + vs, ap - vs);
						atts_store.push_back (aname);
						atts_store.push_back (aval);
						ap++;   /* skip closing quote */
					} else {
						atts_store.push_back (aname);
						atts_store.push_back ("");
					}
				} else {
					atts_store.push_back (aname);
					atts_store.push_back ("");
				}
			}
			for (size_t i = 0; i < atts_store.size (); i++)
				atts_vec.push_back (atts_store[i].c_str ());
			atts_vec.push_back (NULL);

			listener->startElement (name.c_str (), atts_vec.data ());
			if (listener->m_error != UT_OK)
				return listener->m_error;
			if (self_closing) {
				listener->endElement (name.c_str ());
				if (listener->m_error != UT_OK)
					return listener->m_error;
			}
			pos = gt + 1;
		}
		text_start = pos;
	}

	/* trailing character data */
	if (pos > text_start)
		_emit_char_data (listener, data + text_start, pos - text_start);

	return listener->m_error;
}

UT_Error IE_Imp_XML::_loadFile (GsfInput * input)
{
	if (!input)
		return UT_IE_COULDNOTOPEN;
	gsf_off_t sz = gsf_input_size (input);
	if (sz < 0)
		return UT_IE_COULDNOTOPEN;
	const guint8 * bytes = gsf_input_read (input, (size_t)sz, NULL);
	if (!bytes)
		return UT_IE_COULDNOTOPEN;
	return _parse_xml (this, (const char *)bytes, (size_t)sz);
}
