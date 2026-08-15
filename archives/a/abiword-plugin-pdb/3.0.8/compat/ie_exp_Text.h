/* compat/ie_exp_Text.h — OHOS minimal AbiWord text-exporter base shim
 *
 * IE_Exp_Text is the base class for text exporters (IE_Exp_PalmDoc).
 * The real AbiWord implementation walks the PD_Document model; the shim
 * streams the text spans recorded by the PD_Document stub through the
 * virtual _writeBytes() hooks.
 */
#ifndef IE_EXP_TEXT_H
#define IE_EXP_TEXT_H

#include <string>
#include "ie_exp.h"

class IE_Exp_Text : public IE_Exp
{
public:
	IE_Exp_Text (PD_Document * pDocument);
	virtual ~IE_Exp_Text ();

	virtual UT_uint32 _writeBytes (const UT_Byte * pBytes, UT_uint32 length);
	virtual bool _writeBytes (const UT_Byte * sz);

protected:
	virtual UT_Error _writeDocument ();
};

#endif /* IE_EXP_TEXT_H */
