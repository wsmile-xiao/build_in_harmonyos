/* compat/fl_AutoNum.h — OHOS minimal AbiWord fl_AutoNum shim
 *
 * The OPML importer builds bullet lists through the fl_AutoNum class
 * (list auto-numbering).  This shim provides the small surface the plugin
 * uses: shared_ptr typedefs, getLevel/getID/getParentID/setLevel, and the
 * FL_ListType constants.  Do not install; compile-time shim only.
 */
#ifndef FL_AUTONUM_H
#define FL_AUTONUM_H

#include <memory>
#include "ut_types.h"

class PD_Document;

/* FL_ListType (subset of src/text/fmt/xp/fp_types.h) */
typedef int FL_ListType;
#define NUMBERED_LIST    0
#define LOWERCASE_LIST   1
#define UPPERCASE_LIST   2
#define LOWERROMAN_LIST  3
#define UPPERROMAN_LIST  4
#define BULLETED_LIST    5
#define AUTO_LIST_RESERVED 1000

class fl_AutoNum
{
public:
	fl_AutoNum (UT_uint32 id, UT_uint32 parent_id, FL_ListType lType,
	            UT_uint32 start, const gchar * lDelim, const gchar * lDecimal,
	            PD_Document * pDoc, void * pView);
	~fl_AutoNum ();

	UT_uint32   getLevel () const { return m_iLevel; }
	void        setLevel (UT_uint32 level) { m_iLevel = level; }
	UT_uint32   getID () const { return m_iID; }
	UT_uint32   getParentID () const { return m_iParentID; }
	FL_ListType getType () const { return m_List_Type; }

private:
	UT_uint32    m_iID;
	UT_uint32    m_iParentID;
	FL_ListType  m_List_Type;
	UT_uint32    m_iLevel;
};

typedef std::shared_ptr<fl_AutoNum>        fl_AutoNumPtr;
typedef std::shared_ptr<const fl_AutoNum>  fl_AutoNumConstPtr;

#endif /* FL_AUTONUM_H */
