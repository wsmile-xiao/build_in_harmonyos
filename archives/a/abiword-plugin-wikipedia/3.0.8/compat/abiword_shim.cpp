/* compat/abiword_shim.cpp — OHOS minimal AbiWord runtime shim
 *
 * Implementations backing the compat/ headers for the wikipedia plugin.
 * Self-contained; no dependency on the real AbiWord core.
 */
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>

#include "ut_types.h"
#include "ut_debugmsg.h"
#include "ut_string.h"
#include "ut_string_class.h"
#include "ev_EditMethod.h"
#include "ev_Menu_Actions.h"
#include "ev_Menu_Labels.h"
#include "xap_App.h"
#include "xap_Frame.h"
#include "xap_Menu_Layouts.h"
#include "fv_View.h"

/* ================================================================== */
/* debug output                                                       */
/* ================================================================== */

void _UT_OutputMessage (const char * s, ...)
{
	va_list args;
	va_start (args, s);
	vfprintf (stderr, s, args);
	va_end (args);
}

/* ================================================================== */
/* UT_UCS4_strlen                                                     */
/* ================================================================== */

UT_uint32 UT_UCS4_strlen (const UT_UCS4Char * string)
{
	if (!string)
		return 0;
	const UT_UCS4Char * p = string;
	while (*p)
		p++;
	return (UT_uint32)(p - string);
}

/* ================================================================== */
/* EV_EditMethod / EV_EditMethodContainer                             */
/* ================================================================== */

EV_EditMethod::EV_EditMethod (const char * szName, EV_EditMethod_pFn fn,
                              EV_EditMethodType emt, const char * szDescription)
	: m_szName (szName),
	  m_fn (fn),
	  m_CtxtFn (0),
	  m_emt (emt),
	  m_szDescription (szDescription),
	  m_context (0)
{
}

EV_EditMethod::EV_EditMethod (const char * szName, EV_EditMethod_pCtxtFn fn,
                              EV_EditMethodType emt, const char * szDescription,
                              void * context)
	: m_szName (szName),
	  m_fn (0),
	  m_CtxtFn (fn),
	  m_emt (emt),
	  m_szDescription (szDescription),
	  m_context (context)
{
}

EV_EditMethod::~EV_EditMethod ()
{
}

const char * EV_EditMethod::getName () const
{
	return m_szName;
}

const char * EV_EditMethod::getDescription () const
{
	return m_szDescription;
}

EV_EditMethodType EV_EditMethod::getType () const
{
	return m_emt;
}

bool EV_EditMethod::Fn (AV_View * pView, EV_EditMethodCallData * pCallData) const
{
	if (m_CtxtFn)
		return m_CtxtFn (pView, pCallData, m_context);
	if (m_fn)
		return m_fn (pView, pCallData);
	return false;
}

EV_EditMethodContainer::EV_EditMethodContainer ()
{
}

EV_EditMethodContainer::~EV_EditMethodContainer ()
{
	for (size_t i = 0; i < m_vec.size (); i++)
		delete m_vec[i];
}

bool EV_EditMethodContainer::addEditMethod (EV_EditMethod * pem)
{
	if (!pem)
		return false;
	for (size_t i = 0; i < m_vec.size (); i++)
		if (m_vec[i] == pem)
			return false;
	m_vec.push_back (pem);
	return true;
}

bool EV_EditMethodContainer::removeEditMethod (EV_EditMethod * pem)
{
	if (!pem)
		return false;
	for (size_t i = 0; i < m_vec.size (); i++) {
		if (m_vec[i] == pem) {
			m_vec.erase (m_vec.begin () + i);
			return true;
		}
	}
	return false;
}

UT_uint32 EV_EditMethodContainer::countEditMethods ()
{
	return (UT_uint32)m_vec.size ();
}

EV_EditMethod * EV_EditMethodContainer::getNthEditMethod (UT_uint32 ndx)
{
	if (ndx >= m_vec.size ())
		return 0;
	return m_vec[ndx];
}

EV_EditMethod * EV_EditMethodContainer::findEditMethodByName (const char * szName) const
{
	if (!szName)
		return 0;
	for (size_t i = 0; i < m_vec.size (); i++)
		if (m_vec[i]->getName () && strcmp (m_vec[i]->getName (), szName) == 0)
			return m_vec[i];
	return 0;
}

EV_EditMethod * ev_EditMethod_lookup (const char * methodName)
{
	XAP_App * pApp = XAP_App::getApp ();
	if (!pApp)
		return 0;
	return pApp->getEditMethodContainer ()->findEditMethodByName (methodName);
}

/* ================================================================== */
/* EV_Menu_Label / EV_Menu_Action / EV_Menu_ActionSet                 */
/* ================================================================== */

EV_Menu_Label::EV_Menu_Label (XAP_Menu_Id id, const char * szMenuLabel,
                              const char * szStatusMsg)
	: m_id (id),
	  m_stMenuLabel (szMenuLabel ? szMenuLabel : ""),
	  m_stStatusMsg (szStatusMsg ? szStatusMsg : "")
{
}

EV_Menu_Label::~EV_Menu_Label ()
{
}

XAP_Menu_Id EV_Menu_Label::getMenuId () const
{
	return m_id;
}

const char * EV_Menu_Label::getMenuLabel () const
{
	return m_stMenuLabel.c_str ();
}

const char * EV_Menu_Label::getMenuStatusMessage () const
{
	return m_stStatusMsg.c_str ();
}

EV_Menu_Action::EV_Menu_Action (XAP_Menu_Id id,
                                bool bHoldsSubMenu,
                                bool bRaisesDialog,
                                bool bCheckable,
                                bool bRadio,
                                const char * szMethodName,
                                EV_GetMenuItemState_pFn pfnGetState,
                                EV_GetMenuItemComputedLabel_pFn pfnGetLabel,
                                const UT_String & stScriptName)
	: m_id (id),
	  m_bHoldsSubMenu (bHoldsSubMenu),
	  m_bRaisesDialog (bRaisesDialog),
	  m_bCheckable (bCheckable),
	  m_bRadio (bRadio),
	  m_szMethodName (szMethodName ? strdup (szMethodName) : 0),
	  m_pfnGetState (pfnGetState),
	  m_pfnGetLabel (pfnGetLabel),
	  m_stScriptName (stScriptName)
{
}

EV_Menu_Action::~EV_Menu_Action ()
{
	free (m_szMethodName);
}

XAP_Menu_Id EV_Menu_Action::getMenuId () const
{
	return m_id;
}

const char * EV_Menu_Action::getMethodName () const
{
	return m_szMethodName;
}

bool EV_Menu_Action::raisesDialog () const
{
	return m_bRaisesDialog;
}

EV_Menu_ActionSet::EV_Menu_ActionSet ()
{
}

EV_Menu_ActionSet::~EV_Menu_ActionSet ()
{
	for (size_t i = 0; i < m_vec.size (); i++)
		delete m_vec[i];
}

bool EV_Menu_ActionSet::addAction (EV_Menu_Action * pAction)
{
	if (!pAction)
		return false;
	for (size_t i = 0; i < m_vec.size (); i++)
		if (m_vec[i]->getMenuId () == pAction->getMenuId ())
			return false;
	m_vec.push_back (pAction);
	return true;
}

const EV_Menu_Action * EV_Menu_ActionSet::getAction (XAP_Menu_Id id) const
{
	for (size_t i = 0; i < m_vec.size (); i++)
		if (m_vec[i]->getMenuId () == id)
			return m_vec[i];
	return 0;
}

UT_uint32 EV_Menu_ActionSet::countActions () const
{
	return (UT_uint32)m_vec.size ();
}

/* ================================================================== */
/* XAP_Menu_Factory                                                   */
/* ================================================================== */

XAP_Menu_Factory::XAP_Menu_Factory (XAP_App * pApp)
	: m_pApp (pApp), m_maxID (0)
{
}

XAP_Menu_Factory::~XAP_Menu_Factory ()
{
}

XAP_Menu_Id XAP_Menu_Factory::addNewMenuAfter (const char * /*szMenu*/,
                                               const char * /*szLanguage*/,
                                               const XAP_Menu_Id /*afterID*/,
                                               EV_Menu_LayoutFlags /*flags*/,
                                               XAP_Menu_Id newID)
{
	if (newID == 0)
		newID = ++m_maxID;
	if (newID > m_maxID)
		m_maxID = newID;
	return newID;
}

XAP_Menu_Id XAP_Menu_Factory::addNewMenuAfter (const char * /*szMenu*/,
                                               const char * /*szLanguage*/,
                                               const char * /*szAfter*/,
                                               EV_Menu_LayoutFlags /*flags*/,
                                               XAP_Menu_Id menuID)
{
	if (menuID == 0)
		menuID = ++m_maxID;
	if (menuID > m_maxID)
		m_maxID = menuID;
	return menuID;
}

XAP_Menu_Id XAP_Menu_Factory::removeMenuItem (const char * /*szMenu*/,
                                              const char * /*szLanguage*/,
                                              const char * szNuke)
{
	if (!szNuke)
		return 0;
	for (size_t i = 0; i < m_labels.size (); i++) {
		if (strcmp (m_labels[i].first.c_str (), szNuke) == 0) {
			XAP_Menu_Id id = m_labels[i].second;
			m_labels.erase (m_labels.begin () + i);
			return id;
		}
	}
	return 0;
}

XAP_Menu_Id XAP_Menu_Factory::removeMenuItem (const char * /*szMenu*/,
                                              const char * /*szLanguage*/,
                                              XAP_Menu_Id nukeID)
{
	for (size_t i = 0; i < m_labels.size (); i++) {
		if (m_labels[i].second == nukeID) {
			m_labels.erase (m_labels.begin () + i);
			return nukeID;
		}
	}
	return 0;
}

bool XAP_Menu_Factory::addNewLabel (const char * /*szMenu*/,
                                    XAP_Menu_Id newID,
                                    const char * szNewLabel,
                                    const char * /*szNewTooltip*/)
{
	if (!szNewLabel)
		return false;
	m_labels.push_back (std::make_pair (UT_String (szNewLabel), newID));
	return true;
}

bool XAP_Menu_Factory::hasLabel (const char * szNewLabel) const
{
	if (!szNewLabel)
		return false;
	for (size_t i = 0; i < m_labels.size (); i++)
		if (strcmp (m_labels[i].first.c_str (), szNewLabel) == 0)
			return true;
	return false;
}

XAP_Menu_Id XAP_Menu_Factory::getIDForLabel (const char * szNewLabel) const
{
	if (!szNewLabel)
		return 0;
	for (size_t i = 0; i < m_labels.size (); i++)
		if (strcmp (m_labels[i].first.c_str (), szNewLabel) == 0)
			return m_labels[i].second;
	return 0;
}

/* ================================================================== */
/* XAP_App singleton                                                  */
/* ================================================================== */

XAP_App * XAP_App::s_pInstance = 0;

XAP_App * XAP_App::getApp ()
{
	if (!s_pInstance)
		s_pInstance = new XAP_App ();
	return s_pInstance;
}

void XAP_App::shutdown ()
{
	delete s_pInstance;
	s_pInstance = 0;
}

XAP_App::XAP_App ()
	: m_pEMC (new EV_EditMethodContainer ()),
	  m_pActionSet (new EV_Menu_ActionSet ()),
	  m_pMenuFactory (new XAP_Menu_Factory (this))
{
}

XAP_App::~XAP_App ()
{
	delete m_pMenuFactory;
	delete m_pActionSet;
	delete m_pEMC;
}

EV_EditMethodContainer * XAP_App::getEditMethodContainer () const
{
	return m_pEMC;
}

EV_Menu_ActionSet * XAP_App::getMenuActionSet () const
{
	return m_pActionSet;
}

XAP_Menu_Factory * XAP_App::getMenuFactory () const
{
	return m_pMenuFactory;
}

UT_sint32 XAP_App::getFrameCount () const
{
	return 0;
}

XAP_Frame * XAP_App::getFrame (UT_sint32 /*ndx*/) const
{
	return 0;
}

XAP_Frame * XAP_App::getLastFocussedFrame () const
{
	/* Single shim frame; its view carries the selection so the test can
	 * drive Wikipedia_invoke() end-to-end (getCurrentView below). */
	static XAP_Frame * s_frame = new XAP_Frame ();
	return s_frame;
}

bool XAP_App::openURL (const char * url)
{
	m_lastURL = url ? url : "";
	return true;
}

const char * XAP_App::getLastOpenedURL () const
{
	return m_lastURL.c_str ();
}

/* ================================================================== */
/* XAP_Frame                                                          */
/* ================================================================== */

XAP_Frame::XAP_Frame ()
{
}

XAP_Frame::~XAP_Frame ()
{
}

AV_View * XAP_Frame::getCurrentView () const
{
	/* Singleton view; its selection is manipulated by the test before
	 * invoking the plugin's Wikipedia_invoke edit method. */
	static FV_View * s_view = new FV_View ();
	return s_view;
}

void XAP_Frame::rebuildMenus ()
{
}

/* ================================================================== */
/* AV_View / FV_View                                                  */
/* ================================================================== */

AV_View::AV_View ()
{
}

AV_View::~AV_View ()
{
}

FV_View::FV_View ()
	: m_selectionEmpty (true), m_selectionText (0)
{
}

FV_View::~FV_View ()
{
	free (m_selectionText);
}

void FV_View::moveInsPtTo (FV_DocPos /*dp*/, bool /*bClearSelection*/)
{
}

void FV_View::extSelTo (FV_DocPos /*dp*/)
{
}

bool FV_View::isSelectionEmpty (void) const
{
	return m_selectionEmpty;
}

void FV_View::getSelectionText (UT_UCS4Char *& text) const
{
	text = 0;
	if (!m_selectionText)
		return;
	size_t len = UT_UCS4_strlen (m_selectionText);
	text = (UT_UCS4Char *)malloc ((len + 1) * sizeof (UT_UCS4Char));
	if (!text)
		return;
	memcpy (text, m_selectionText, (len + 1) * sizeof (UT_UCS4Char));
}

void FV_View::setSelectionText (const UT_UCS4Char * text)
{
	free (m_selectionText);
	m_selectionText = 0;
	if (text) {
		size_t len = UT_UCS4_strlen (text);
		m_selectionText = (UT_UCS4Char *)malloc ((len + 1) * sizeof (UT_UCS4Char));
		if (m_selectionText)
			memcpy (m_selectionText, text, (len + 1) * sizeof (UT_UCS4Char));
	}
	m_selectionEmpty = (m_selectionText == 0 || m_selectionText[0] == 0);
}
