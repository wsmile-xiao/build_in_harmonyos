/* compat/ie_exp.h — OHOS minimal AbiWord ie_exp.h shim
 *
 * Included by AbiGeneric.h; the AbiPaint plugin does not use the
 * exporter framework directly.
 */
#ifndef IE_EXP_H
#define IE_EXP_H

#include "ut_types.h"

class PD_Document;

class IE_ExpSniffer
{
public:
	virtual ~IE_ExpSniffer () {}
};

class IE_Exp
{
public:
	virtual ~IE_Exp () {}
};

#endif /* IE_EXP_H */
