/* compat/pd_Document.h — OHOS minimal AbiWord pd_Document.h shim
 * Referenced by fg_Graphic.h; the paint plugin does not touch the
 * document model directly.
 */
#ifndef PD_DOCUMENT_H
#define PD_DOCUMENT_H

#include "ut_types.h"

class PD_Document
{
public:
	PD_Document ();
	~PD_Document ();
};

#endif /* PD_DOCUMENT_H */
