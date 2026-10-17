/* compat/abiword_shim.cpp — OHOS minimal AbiWord runtime shim
 *
 * Implementations backing the compat/ headers for the AbiPaint plugin.
 * Self-contained; no dependency on the real AbiWord core.
 *
 * The AbiPaint plugin module calls into the XAP/EV/FV APIs below during
 * abi_plugin_register()/abi_plugin_unregister() (preferences, menus,
 * edit methods, views).  This shim makes those calls work end-to-end so
 * the module can be dlopened and driven by tests without AbiWord.
 */
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

#include "ut_types.h"
#include "ut_assert.h"
#include "ut_debugmsg.h"
#include "ut_path.h"
#include "ut_vector.h"
#include "xap_App.h"
#include "xap_Frame.h"
#include "xap_Prefs.h"
#include "xap_DialogFactory.h"
#include "xap_Dlg_FileOpenSaveAs.h"
#include "xap_Dlg_MessageBox.h"
#include "xap_Menu_Layouts.h"
#include "ap_Dialog_Id.h"
#include "ev_EditMethod.h"
#include "ev_Menu.h"
#include "ev_Menu_Actions.h"
#include "ev_Menu_Labels.h"
#include "ev_Menu_Layouts.h"
#include "fv_View.h"
#include "ie_impGraphic.h"
#include "pd_Document.h"

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
/* GLib shim                                                          */
/* ================================================================== */

void g_free (gpointer mem)
{
	free (mem);
}

void g_warning (const char * format, ...)
{
	va_list args;
	va_start (args, format);
	fprintf (stderr, "WARNING: ");
	vfprintf (stderr, format, args);
	fprintf (stderr, "\n");
	va_end (args);
}

void g_error_free (GError * err)
{
	if (!err)
		return;
	g_free (err->message);
	free (err);
}

void g_usleep (unsigned long usec)
{
	struct timespec ts;
	ts.tv_sec = (time_t)(usec / 1000000UL);
	ts.tv_nsec = (long)((usec % 1000000UL) * 1000UL);
	nanosleep (&ts, 0);
}

gint g_file_open_tmp (const char * tmpl, gchar ** name_used, GError ** error)
{
	if (!tmpl || !name_used)
		return -1;
	char * fn = strdup (tmpl);
	if (!fn)
		return -1;
	int fd = mkstemp (fn);
	if (fd < 0) {
		if (error && !*error) {
			*error = (GError *)calloc (1, sizeof (GError));
			if (*error)
				(*error)->message = strdup ("g_file_open_tmp: mkstemp failed");
		}
		free (fn);
		return -1;
	}
	*name_used = fn;
	return fd;
}

/* ================================================================== */
/* ut_path                                                            */
/* ================================================================== */

const char * UT_basename (const char * path)
{
	if (!path || !*path)
		return path;
	const char * p = strrchr (path, '/');
	if (p && p[1])
		return p + 1;
	/* 路径以 '/' 结尾（如 "a/b/"）时，最后一个组件为空：返回 p+1
	 * （指向结尾的 NUL）；无 '/' 时返回整个 path。 */
	return p ? p + 1 : path;
}

bool UT_isRegularFile (const char * filename)
{
	struct stat st;
	if (!filename || stat (filename, &st) != 0)
		return false;
	return S_ISREG (st.st_mode) != 0;
}

bool UT_directoryExists (const char * dir)
{
	struct stat st;
	if (!dir || stat (dir, &st) != 0)
		return false;
	return S_ISDIR (st.st_mode) != 0;
}

/* ================================================================== */
/* PD_Document stub                                                   */
/* ================================================================== */

PD_Document::PD_Document () {}
PD_Document::~PD_Document () {}

/* ================================================================== */
/* XAP_App singleton                                                  */
/* ================================================================== */

static XAP_Frame * s_pFrame = 0;
static FV_View *   s_pView  = 0;

static XAP_App * s_pApp = 0;

XAP_App::XAP_App ()
{
	s_pFrame = new XAP_Frame ();
	s_pView  = new FV_View ();
	s_pFrame->_test_setCurrentView (s_pView);
}

XAP_App::~XAP_App ()
{
	delete s_pView;  s_pView = 0;
	delete s_pFrame; s_pFrame = 0;
}

XAP_App * XAP_App::getApp ()
{
	if (!s_pApp) {
		s_pApp = new XAP_App ();
		s_pApp->getPrefs ();
		s_pApp->getEditMethodContainer ();
		s_pApp->getMenuFactory ();
		s_pApp->getMenuActionSet ();
	}
	return s_pApp;
}

void XAP_App::_test_clear ()
{
	if (s_pApp) {
		delete s_pApp;
		s_pApp = 0;
	}
}

XAP_Prefs * XAP_App::getPrefs () const
{
	static XAP_Prefs * s_pPrefs = 0;
	if (!s_pPrefs)
		s_pPrefs = new XAP_Prefs ();
	return s_pPrefs;
}

EV_EditMethodContainer * XAP_App::getEditMethodContainer () const
{
	static EV_EditMethodContainer * s_pEMC = 0;
	if (!s_pEMC)
		s_pEMC = new EV_EditMethodContainer ();
	return s_pEMC;
}

EV_Menu_ActionSet * XAP_App::getMenuActionSet () const
{
	static EV_Menu_ActionSet * s_pAS = 0;
	if (!s_pAS)
		s_pAS = new EV_Menu_ActionSet ();
	return s_pAS;
}

XAP_Menu_Factory * XAP_App::getMenuFactory () const
{
	static XAP_Menu_Factory * s_pMF = 0;
	if (!s_pMF)
		s_pMF = new XAP_Menu_Factory (const_cast<XAP_App *>(this));
	return s_pMF;
}

UT_sint32 XAP_App::getFrameCount () const
{
	return s_pFrame ? 1 : 0;
}

XAP_Frame * XAP_App::getFrame (UT_sint32 /*ndx*/) const
{
	return s_pFrame;
}

XAP_Frame * XAP_App::getLastFocussedFrame () const
{
	return s_pFrame;
}

/* ================================================================== */
/* XAP_Frame                                                          */
/* ================================================================== */

XAP_Frame::XAP_Frame () {}
XAP_Frame::~XAP_Frame () {}

AV_View * XAP_Frame::getCurrentView () const
{
	return s_pView;
}

void XAP_Frame::_test_setCurrentView (AV_View * v)
{
	(void)v;
}

XAP_DialogFactory * XAP_Frame::getDialogFactory ()
{
	static XAP_DialogFactory * s_pDF = 0;
	if (!s_pDF)
		s_pDF = new XAP_DialogFactory (XAP_App::getApp (), this);
	return s_pDF;
}

void XAP_Frame::nullUpdate () const {}

const char * XAP_Frame::getFilename () const
{
	return "";
}

void XAP_Frame::rebuildMenus () {}

XAP_Dialog_MessageBox::tAnswer XAP_Frame::showMessageBox (
	const char * /*sz*/,
	XAP_Dialog_MessageBox::tButtons /*buttons*/,
	XAP_Dialog_MessageBox::tAnswer /*answer*/)
{
	return XAP_Dialog_MessageBox::a_OK;
}

/* ================================================================== */
/* XAP_Prefs / XAP_PrefsScheme                                        */
/* ================================================================== */

XAP_PrefsScheme::XAP_PrefsScheme (XAP_Prefs * /*pPrefs*/, const gchar * szSchemeName)
	: m_szName (szSchemeName ? szSchemeName : "")
{
}

XAP_PrefsScheme::~XAP_PrefsScheme () {}

bool XAP_PrefsScheme::setValue (const gchar * szKey, const gchar * szValue)
{
	if (!szKey)
		return false;
	m_hash[szKey] = szValue ? szValue : "";
	return true;
}

bool XAP_PrefsScheme::setValueBool (const gchar * szKey, bool bValue)
{
	return setValue (szKey, bValue ? "1" : "0");
}

bool XAP_PrefsScheme::getValue (const gchar * szKey, const gchar ** pszValue) const
{
	if (!szKey || !pszValue)
		return false;
	std::map<std::string, std::string>::const_iterator it = m_hash.find (szKey);
	if (it == m_hash.end ())
		return false;
	*pszValue = it->second.c_str ();
	return true;
}

bool XAP_PrefsScheme::getValue (const char * szKey, std::string & szValue) const
{
	if (!szKey)
		return false;
	std::map<std::string, std::string>::const_iterator it = m_hash.find (szKey);
	if (it == m_hash.end ())
		return false;
	szValue = it->second;
	return true;
}

bool XAP_PrefsScheme::getValueBool (const gchar * szKey, bool * pbValue) const
{
	const gchar * v = 0;
	if (!getValue (szKey, &v))
		return false;
	if (pbValue)
		*pbValue = (v && *v == '1');
	return true;
}

const gchar * XAP_PrefsScheme::getSchemeName () const
{
	return m_szName.c_str ();
}

bool XAP_PrefsScheme::_test_has (const gchar * szKey) const
{
	return szKey && m_hash.find (szKey) != m_hash.end ();
}

XAP_Prefs::XAP_Prefs () {}
XAP_Prefs::~XAP_Prefs () {}

XAP_PrefsScheme * XAP_Prefs::getPluginScheme (const gchar * szSchemeName) const
{
	if (!szSchemeName)
		return 0;
	for (UT_uint32 i = 0; i < m_vecPluginSchemes.getItemCount (); i++) {
		XAP_PrefsScheme * s = m_vecPluginSchemes.getNthItem (i);
		if (s && strcmp (s->getSchemeName (), szSchemeName) == 0)
			return s;
	}
	return 0;
}

bool XAP_Prefs::addPluginScheme (XAP_PrefsScheme * pNewScheme)
{
	if (!pNewScheme)
		return false;
	if (getPluginScheme (pNewScheme->getSchemeName ()))
		return false;
	return m_vecPluginSchemes.addItem (pNewScheme);
}

UT_uint32 XAP_Prefs::getPluginSchemeCount () const
{
	return m_vecPluginSchemes.getItemCount ();
}

/* ================================================================== */
/* Dialogs                                                            */
/* ================================================================== */

XAP_Dialog::XAP_Dialog (XAP_DialogFactory * pDlgFactory, XAP_Dialog_Id id, const char *)
	: m_pDlgFactory (pDlgFactory), m_id (id)
{
}

XAP_Dialog::~XAP_Dialog () {}

XAP_DialogFactory::XAP_DialogFactory (XAP_App * pApp, XAP_Frame * pFrame)
	: m_pApp (pApp), m_pFrame (pFrame)
{
}

XAP_DialogFactory::~XAP_DialogFactory () {}

XAP_Dialog * XAP_DialogFactory::requestDialog (XAP_Dialog_Id id)
{
	if (id == XAP_DIALOG_ID_FILE_OPEN || id == XAP_DIALOG_ID_FILE_SAVEAS)
		return new XAP_Dialog_FileOpenSaveAs (this, id);
	return new XAP_Dialog_MessageBox (this, id);
}

void XAP_DialogFactory::releaseDialog (XAP_Dialog * pDialog)
{
	delete pDialog;
}

XAP_Dialog_FileOpenSaveAs::XAP_Dialog_FileOpenSaveAs (XAP_DialogFactory * pDlgFactory, XAP_Dialog_Id id)
	: XAP_Dialog (pDlgFactory, id), m_szFinalPathname (0), m_answer (a_CANCEL)
{
}

XAP_Dialog_FileOpenSaveAs::~XAP_Dialog_FileOpenSaveAs ()
{
	g_free (m_szFinalPathname);
}

void XAP_Dialog_FileOpenSaveAs::runModal (XAP_Frame * /*pFrame*/)
{
	m_answer = a_CANCEL;   /* headless: no user interaction */
}

void XAP_Dialog_FileOpenSaveAs::setCurrentPathname (const char * szPathname)
{
	g_free (m_szFinalPathname);
	m_szFinalPathname = szPathname ? strdup (szPathname) : 0;
}

void XAP_Dialog_FileOpenSaveAs::setSuggestFilename (bool /*bSuggest*/) {}

void XAP_Dialog_FileOpenSaveAs::setFileTypeList (const char ** /*szDescriptions*/,
                                                 const char ** /*szSuffixes*/,
                                                 const UT_sint32 * /*nTypeList*/) {}

XAP_Dialog_FileOpenSaveAs::tAnswer XAP_Dialog_FileOpenSaveAs::getAnswer () const
{
	return m_answer;
}

const char * XAP_Dialog_FileOpenSaveAs::getPathname () const
{
	return m_szFinalPathname ? m_szFinalPathname : "";
}

XAP_Dialog_MessageBox::XAP_Dialog_MessageBox (XAP_DialogFactory * pDlgFactory, XAP_Dialog_Id id)
	: XAP_Dialog (pDlgFactory, id), m_buttons (b_O), m_answer (a_OK)
{
}

XAP_Dialog_MessageBox::~XAP_Dialog_MessageBox () {}

void XAP_Dialog_MessageBox::runModal (XAP_Frame * /*pFrame*/)
{
	m_answer = a_OK;
}

/* ================================================================== */
/* EV_EditMethod framework                                            */
/* ================================================================== */

EV_EditMethodCallData::EV_EditMethodCallData ()
	: m_pData (0), m_dataLength (0), m_bAllocatedData (false), m_xPos (0), m_yPos (0)
{
}

EV_EditMethodCallData::EV_EditMethodCallData (const UT_UCSChar * pData, UT_uint32 dataLength)
	: m_pData (const_cast<UT_UCSChar *>(pData)), m_dataLength (dataLength),
	  m_bAllocatedData (false), m_xPos (0), m_yPos (0)
{
}

EV_EditMethodCallData::~EV_EditMethodCallData ()
{
	if (m_bAllocatedData)
		g_free (m_pData);
}

EV_EditMethod::EV_EditMethod (const char * szName, EV_EditMethod_pFn fn,
                              EV_EditMethodType emt, const char * szDescription)
	: m_szName (szName ? szName : ""), m_fn (fn), m_emt (emt),
	  m_szDescription (szDescription ? szDescription : "")
{
}

bool EV_EditMethod::Fn (AV_View * pView, EV_EditMethodCallData * pCallData) const
{
	return m_fn ? m_fn (pView, pCallData) : false;
}

const char * EV_EditMethod::getName () const
{
	return m_szName;
}

const char * EV_EditMethod::getDescription () const
{
	return m_szDescription;
}

/* global edit-method registry (so ev_EditMethod_lookup works like the
 * real AbiWord static lookup) */
static UT_GenericVector<EV_EditMethod *> & edit_method_registry ()
{
	static UT_GenericVector<EV_EditMethod *> reg;
	return reg;
}

EV_EditMethodContainer::EV_EditMethodContainer () {}
EV_EditMethodContainer::~EV_EditMethodContainer () {}

bool EV_EditMethodContainer::addEditMethod (EV_EditMethod * pem)
{
	if (!pem)
		return false;
	/* keep the global registry in sync with the per-app container */
	if (findEditMethodByName (pem->getName ()))
		return false;
	if (!m_vecDynamicEditMethods.addItem (pem))
		return false;
	edit_method_registry ().addItem (pem);
	return true;
}

bool EV_EditMethodContainer::removeEditMethod (EV_EditMethod * pem)
{
	if (!pem)
		return false;
	UT_uint32 ndx;
	if (m_vecDynamicEditMethods.findItem (pem, &ndx))
		m_vecDynamicEditMethods.deleteNthItem (ndx);
	if (edit_method_registry ().findItem (pem, &ndx))
		edit_method_registry ().deleteNthItem (ndx);
	return true;
}

UT_uint32 EV_EditMethodContainer::countEditMethods ()
{
	return m_vecDynamicEditMethods.getItemCount ();
}

EV_EditMethod * EV_EditMethodContainer::getNthEditMethod (UT_uint32 ndx)
{
	return m_vecDynamicEditMethods.getNthItem (ndx);
}

EV_EditMethod * EV_EditMethodContainer::findEditMethodByName (const char * szName) const
{
	if (!szName)
		return 0;
	for (UT_uint32 i = 0; i < m_vecDynamicEditMethods.getItemCount (); i++) {
		EV_EditMethod * e = m_vecDynamicEditMethods.getNthItem (i);
		if (e && strcmp (e->getName (), szName) == 0)
			return e;
	}
	return 0;
}

EV_EditMethod * ev_EditMethod_lookup (const char * methodName)
{
	if (!methodName)
		return 0;
	for (UT_uint32 i = 0; i < edit_method_registry ().getItemCount (); i++) {
		EV_EditMethod * e = edit_method_registry ().getNthItem (i);
		if (e && strcmp (e->getName (), methodName) == 0)
			return e;
	}
	return 0;
}

bool ev_EditMethod_invoke (const EV_EditMethod * pEM, EV_EditMethodCallData * pData)
{
	return pEM ? pEM->Fn (0, pData) : false;
}

EV_Menu::~EV_Menu () {}

/* ================================================================== */
/* Menu labels / actions / factory                                    */
/* ================================================================== */

EV_Menu_Label::EV_Menu_Label (XAP_Menu_Id id, const char * szMenuLabel, const char * szStatusMsg)
	: m_id (id), m_stMenuLabel (szMenuLabel ? szMenuLabel : ""),
	  m_stStatusMsg (szStatusMsg ? szStatusMsg : "")
{
}

EV_Menu_Label::~EV_Menu_Label () {}

XAP_Menu_Id EV_Menu_Label::getMenuId () const { return m_id; }
const char * EV_Menu_Label::getMenuLabel () const { return m_stMenuLabel.c_str (); }
const char * EV_Menu_Label::getMenuStatusMessage () const { return m_stStatusMsg.c_str (); }

EV_Menu_Action::EV_Menu_Action (XAP_Menu_Id id, bool bHoldsSubMenu, bool bRaisesDialog,
                                bool bCheckable, bool bRadio, const char * szMethodName,
                                EV_GetMenuItemState_pFn pfnGetState,
                                EV_GetMenuItemComputedLabel_pFn pfnGetLabel,
                                const UT_String & stScriptName)
	: m_id (id), m_bHoldsSubMenu (bHoldsSubMenu), m_bRaisesDialog (bRaisesDialog),
	  m_bCheckable (bCheckable), m_bRadio (bRadio),
	  m_szMethodName (szMethodName ? strdup (szMethodName) : 0),
	  m_pfnGetState (pfnGetState), m_pfnGetLabel (pfnGetLabel),
	  m_stScriptName (stScriptName)
{
}

EV_Menu_Action::~EV_Menu_Action ()
{
	g_free (m_szMethodName);
}

XAP_Menu_Id EV_Menu_Action::getMenuId () const { return m_id; }
const char * EV_Menu_Action::getMethodName () const { return m_szMethodName ? m_szMethodName : ""; }
bool EV_Menu_Action::raisesDialog () const { return m_bRaisesDialog; }
bool EV_Menu_Action::isCheckable () const { return m_bCheckable; }
bool EV_Menu_Action::isRadio () const { return m_bRadio; }
bool EV_Menu_Action::hasGetStateFunction () const { return m_pfnGetState != 0; }
bool EV_Menu_Action::hasDynamicLabel () const { return m_pfnGetLabel != 0; }

EV_Menu_ItemState EV_Menu_Action::getMenuItemState (AV_View * pView) const
{
	return m_pfnGetState ? m_pfnGetState (pView, m_id) : EV_MIS_ZERO;
}

const char * EV_Menu_Action::getDynamicLabel (const EV_Menu_Label * pLabel) const
{
	return m_pfnGetLabel ? m_pfnGetLabel (pLabel, m_id) : 0;
}

EV_Menu_ActionSet::EV_Menu_ActionSet () {}
EV_Menu_ActionSet::~EV_Menu_ActionSet () {}

bool EV_Menu_ActionSet::addAction (EV_Menu_Action * pAction)
{
	if (!pAction)
		return false;
	return m_actionTable.addItem (pAction);
}

const EV_Menu_Action * EV_Menu_ActionSet::getAction (XAP_Menu_Id id) const
{
	for (UT_uint32 i = 0; i < m_actionTable.getItemCount (); i++) {
		const EV_Menu_Action * a = m_actionTable.getNthItem (i);
		if (a && a->getMenuId () == id)
			return a;
	}
	return 0;
}

UT_uint32 EV_Menu_ActionSet::getActionCount () const
{
	return m_actionTable.getItemCount ();
}

XAP_Menu_Factory::XAP_Menu_Factory (XAP_App * pApp)
	: m_pApp (pApp), m_maxID (1000)
{
}

XAP_Menu_Factory::~XAP_Menu_Factory () {}

XAP_Menu_Id XAP_Menu_Factory::getNewID (void)
{
	return ++m_maxID;
}

bool XAP_Menu_Factory::addNewLabel (const char * /*szMenu*/, XAP_Menu_Id /*newID*/,
                                    const char * /*szNewLabel*/, const char * /*szNewTooltip*/)
{
	return true;
}

XAP_Menu_Id XAP_Menu_Factory::addNewMenuAfter (const char * /*szMenu*/, const char * /*szLanguage*/,
                                               const XAP_Menu_Id /*afterID*/,
                                               EV_Menu_LayoutFlags /*flags*/, XAP_Menu_Id newID)
{
	if (newID == 0)
		newID = getNewID ();
	m_menuItems.addItem (newID);
	return newID;
}

XAP_Menu_Id XAP_Menu_Factory::removeMenuItem (const char * /*szMenu*/, const char * /*szLanguage*/,
                                              XAP_Menu_Id nukeID)
{
	UT_uint32 ndx;
	if (m_menuItems.findItem (nukeID, &ndx))
		m_menuItems.deleteNthItem (ndx);
	return nukeID;
}

UT_uint32 XAP_Menu_Factory::_test_menuCount () const
{
	return m_menuItems.getItemCount ();
}

/* ================================================================== */
/* FV_View                                                            */
/* ================================================================== */

FV_View::FV_View () : m_inserted (0) {}
FV_View::~FV_View () {}

PT_DocPosition FV_View::saveSelectedImage (const char * /*toFile*/)
{
	return 0;   /* no image selected in the headless shim */
}

PT_DocPosition FV_View::getSelectedImage (const char ** /*dataId*/) const
{
	return 0;   /* no image selected */
}

void FV_View::cmdUnselectSelection (void) {}
void FV_View::setPoint (UT_uint32 /*pt*/) {}
void FV_View::extSelHorizontal (bool /*bForward*/, UT_uint32 /*count*/) {}

UT_Error FV_View::cmdInsertGraphic (FG_Graphic * /*pFG*/)
{
	m_inserted++;
	return UT_OK;
}

/* ================================================================== */
/* IE_ImpGraphic                                                      */
/* ================================================================== */

UT_Error IE_ImpGraphic::loadGraphic (const char * /*szFilename*/,
                                     IEGraphicFileType /*iegft*/,
                                     FG_Graphic ** ppfg)
{
	if (ppfg)
		*ppfg = 0;
	return UT_IE_IMPORTERROR;
}
