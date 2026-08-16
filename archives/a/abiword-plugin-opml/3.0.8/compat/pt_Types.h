/* compat/pt_Types.h — OHOS minimal AbiWord pt_Types.h shim
 *
 * Provides the PTStruxType / PTObjectType enums and the PT_* attribute-name
 * macros used by the OPML import plugin (and the AbiWord importer base
 * classes in this compat tree).  Mirrors the surface of
 * src/text/ptbl/xp/pt_Types.h.  Do not install; compile-time shim only.
 */
#ifndef PT_TYPES_H
#define PT_TYPES_H

#include "ut_types.h"

/* PTStruxType: the document structural elements an importer appends via
 * PD_Document::appendStrux */
typedef enum _PTStruxType
{
	PTX_Section = 0,
	PTX_Block,
	PTX_SectionHdrFtr,
	PTX_SectionEndnote,
	PTX_SectionTable,
	PTX_SectionCell,
	PTX_SectionFootnote,
	PTX_SectionMarginnote,
	PTX_SectionAnnotation,
	PTX_SectionFrame,
	PTX_SectionTOC,
	PTX_Endnote,
	PTX_Annotation,
	PTX_StruxDummy
} PTStruxType;

/* PTObjectType: sub-type of a FragObject */
typedef enum _PTObjectType
{
	PTO_Image = 0,
	PTO_Field,
	PTO_Bookmark,
	PTO_Hyperlink,
	PTO_Math,
	PTO_Embed,
	PTO_Annotation,
	PTO_RDFAnchor
} PTObjectType;

/* attribute names used in strux / object / format attribute arrays */
#define PT_PROPS_ATTRIBUTE_NAME		(static_cast<const gchar *>("props"))
#define PT_STYLE_ATTRIBUTE_NAME		(static_cast<const gchar *>("style"))
#define PT_LEVEL_ATTRIBUTE_NAME		(static_cast<const gchar *>("level"))
#define PT_LISTID_ATTRIBUTE_NAME	(static_cast<const gchar *>("listid"))
#define PT_PARENTID_ATTRIBUTE_NAME	(static_cast<const gchar *>("parentid"))
#define PT_NAME_ATTRIBUTE_NAME		(static_cast<const gchar *>("name"))
#define PT_TYPE_ATTRIBUTE_NAME		(static_cast<const gchar *>("type"))

#endif /* PT_TYPES_H */
