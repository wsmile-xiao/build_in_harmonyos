/* compat/ie_imp.h — OHOS minimal AbiWord ie_imp.h shim
 *
 * Included by AbiGeneric.h; the AbiPaint plugin does not use the
 * importer framework directly, so only minimal declarations are
 * provided.
 */
#ifndef IE_IMP_H
#define IE_IMP_H

#include "ut_types.h"
#include "ie_types.h"

class PD_Document;

class IE_ImpSniffer
{
public:
	virtual ~IE_ImpSniffer () {}
};

class IE_Imp
{
public:
	virtual ~IE_Imp () {}
};

#endif /* IE_IMP_H */
