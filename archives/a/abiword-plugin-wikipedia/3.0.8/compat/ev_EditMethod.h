/* compat/ev_EditMethod.h — OHOS minimal AbiWord edit-method shim
 *
 * The wikipedia plugin registers one EditMethod ("Wikipedia_invoke"),
 * looks it up on unload and removes it.  The container keeps a dynamic
 * registry so the end-to-end test can observe add/lookup/remove.
 */
#ifndef EV_EDITMETHOD_H
#define EV_EDITMETHOD_H

#include <vector>
#include "ut_types.h"
#include "ut_string_class.h"

class AV_View;

typedef UT_uint32 EV_EditMethodType;
#define EV_EMT_REQUIREDATA       ((EV_EditMethodType)0x1)
#define EV_EMT_REQUIRE_SCRIPT_NAME ((EV_EditMethodType)0x2)
#define EV_EMT_APP_METHOD        ((EV_EditMethodType)0x4)

class ABI_EXPORT EV_EditMethodCallData
{
public:
	EV_EditMethodCallData () : m_pData (0), m_dataLength (0) {}

	UT_UCSChar * m_pData;
	UT_uint32    m_dataLength;
};

typedef bool (*EV_EditMethod_pFn)(AV_View * pView, EV_EditMethodCallData * pCallData);
typedef bool (*EV_EditMethod_pCtxtFn)(AV_View * pView, EV_EditMethodCallData * pCallData,
                                      void * context);

class ABI_EXPORT EV_EditMethod
{
public:
	EV_EditMethod (const char * szName, EV_EditMethod_pFn fn, EV_EditMethodType emt,
	               const char * szDescription);
	EV_EditMethod (const char * szName, EV_EditMethod_pCtxtFn fn, EV_EditMethodType emt,
	               const char * szDescription, void * context);
	~EV_EditMethod ();

	const char *      getName () const;
	const char *      getDescription () const;
	EV_EditMethodType getType () const;
	bool              Fn (AV_View * pView, EV_EditMethodCallData * pCallData) const;

private:
	const char *         m_szName;
	EV_EditMethod_pFn    m_fn;
	EV_EditMethod_pCtxtFn m_CtxtFn;
	EV_EditMethodType    m_emt;
	const char *         m_szDescription;
	void *               m_context;
};

class ABI_EXPORT EV_EditMethodContainer
{
public:
	EV_EditMethodContainer ();
	~EV_EditMethodContainer ();

	bool                addEditMethod (EV_EditMethod * pem);
	bool                removeEditMethod (EV_EditMethod * pem);
	UT_uint32           countEditMethods ();
	EV_EditMethod *     getNthEditMethod (UT_uint32 ndx);
	EV_EditMethod *     findEditMethodByName (const char * szName) const;

private:
	std::vector<EV_EditMethod *> m_vec;
};

ABI_EXPORT EV_EditMethod * ev_EditMethod_lookup (const char * methodName);

#endif /* EV_EDITMETHOD_H */
