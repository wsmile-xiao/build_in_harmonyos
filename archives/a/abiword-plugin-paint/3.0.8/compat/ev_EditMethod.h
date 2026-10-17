/* compat/ev_EditMethod.h — OHOS minimal AbiWord ev_EditMethod.h shim */
#ifndef EV_EDITMETHOD_H
#define EV_EDITMETHOD_H

#include "ut_types.h"

class AV_View;

/*****************************************************************/

typedef UT_uint32 EV_EditMethodType;

/*****************************************************************/

class EV_EditMethodCallData
{
public:
	EV_EditMethodCallData ();
	EV_EditMethodCallData (const UT_UCSChar * pData, UT_uint32 dataLength);
	~EV_EditMethodCallData ();

	UT_sint32       getX () { return m_xPos; }
	UT_sint32       getY () { return m_yPos; }

private:
	UT_UCSChar *    m_pData;
	UT_uint32       m_dataLength;
	bool            m_bAllocatedData;
	UT_sint32       m_xPos;
	UT_sint32       m_yPos;
};

typedef bool (*EV_EditMethod_pFn)(AV_View * pView, EV_EditMethodCallData * pCallData);
typedef bool ( EV_EditMethod_Fn) (AV_View * pView, EV_EditMethodCallData * pCallData);

/*****************************************************************/

class EV_EditMethod
{
public:
	EV_EditMethod (const char * szName, EV_EditMethod_pFn fn, EV_EditMethodType emt,
	               const char * szDescription);

	bool                 Fn (AV_View * pView, EV_EditMethodCallData * pCallData) const;
	const char *         getName () const;
	const char *         getDescription () const;

protected:
	const char *         m_szName;
	EV_EditMethod_pFn    m_fn;
	EV_EditMethodType    m_emt;
	const char *         m_szDescription;
};

/*****************************************************************/

class EV_EditMethodContainer
{
public:
	EV_EditMethodContainer ();
	~EV_EditMethodContainer ();

	bool              addEditMethod (EV_EditMethod * pem);
	bool              removeEditMethod (EV_EditMethod * pem);
	UT_uint32         countEditMethods ();
	EV_EditMethod *   getNthEditMethod (UT_uint32 ndx);
	EV_EditMethod *   findEditMethodByName (const char * szName) const;

private:
	UT_GenericVector<EV_EditMethod *> m_vecDynamicEditMethods;
};

/*****************************************************************/

EV_EditMethod * ev_EditMethod_lookup (const char * methodName);
bool            ev_EditMethod_invoke (const EV_EditMethod * pEM, EV_EditMethodCallData * pData);

#endif /* EV_EDITMETHOD_H */
