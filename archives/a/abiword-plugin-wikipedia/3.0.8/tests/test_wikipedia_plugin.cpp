/* tests/test_wikipedia_plugin.cpp — OHOS end-to-end test for the
 * abiword-plugin-wikipedia module.
 *
 * Verifies (R34: substantive use of the package API):
 *   1. the plugin module dlopens and abi_plugin_register() fills
 *      XAP_ModuleInfo;
 *   2. after register, the app's EV_EditMethodContainer contains the
 *      "Wikipedia_invoke" edit method (ev_EditMethod_lookup hits);
 *   3. the XAP_Menu_Factory has the "Wi&ki Encyclopedia" label and the
 *      matching EV_Menu_ActionSet entry bound to "Wikipedia_invoke";
 *   4. invoking the edit method with a selected word drives openURL()
 *      to the expected Wikipedia search URL (end-to-end);
 *   5. abi_plugin_supports_version() reports 1;
 *   6. after abi_plugin_unregister() the edit method and the menu label
 *      are removed.
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "ut_types.h"
#include "ut_assert.h"
#include "ut_string_class.h"
#include "xap_Module.h"
#include "xap_App.h"
#include "xap_Frame.h"
#include "ev_EditMethod.h"
#include "ev_Menu_Actions.h"
#include "xap_Menu_Layouts.h"
#include "fv_View.h"

typedef int (*plugin_reg_fn)   (XAP_ModuleInfo * mi);
typedef int (*plugin_unreg_fn) (XAP_ModuleInfo * mi);
typedef int (*plugin_ver_fn)   (UT_uint32 major, UT_uint32 minor, UT_uint32 release);

static int failures = 0;
static int checks   = 0;

#define CHECK(cond, msg)                                                     \
	do {                                                                     \
		checks++;                                                            \
		if (cond) {                                                          \
			printf ("  [OK] %s\n", msg);                                     \
		} else {                                                             \
			printf ("  [FAIL] %s\n", msg);                                   \
			failures++;                                                      \
		}                                                                    \
	} while (0)

int main (void)
{
	const char * so_path = getenv ("PLUGIN_SO");

	CHECK (so_path && so_path[0], "PLUGIN_SO env set");
	if (!so_path)
		return 1;

	/* ---- 1. dlopen the plugin module ---- */
	void * handle = dlopen (so_path, RTLD_NOW | RTLD_LOCAL);
	CHECK (handle != 0, "dlopen(plugin .so)");
	if (!handle) {
		fprintf (stderr, "  dlopen error: %s\n", dlerror ());
		return 1;
	}

	plugin_reg_fn   reg   = (plugin_reg_fn)dlsym (handle, "abi_plugin_register");
	plugin_unreg_fn unreg = (plugin_unreg_fn)dlsym (handle, "abi_plugin_unregister");
	plugin_ver_fn   ver   = (plugin_ver_fn)dlsym (handle, "abi_plugin_supports_version");
	CHECK (reg != 0, "dlsym(abi_plugin_register)");
	CHECK (unreg != 0, "dlsym(abi_plugin_unregister)");
	CHECK (ver != 0, "dlsym(abi_plugin_supports_version)");
	if (!reg || !unreg || !ver) {
		dlclose (handle);
		return 1;
	}

	XAP_ModuleInfo mi;
	memset (&mi, 0, sizeof (mi));

	/* ---- 2. register ---- */
	int r = reg (&mi);
	CHECK (r == 1, "abi_plugin_register() returns 1");
	CHECK (mi.name && strcmp (mi.name, "Wikipedia plugin") == 0, "XAP_ModuleInfo.name filled");
	CHECK (mi.desc && strstr (mi.desc, "wikipedia.com") != 0, "XAP_ModuleInfo.desc filled");
	CHECK (mi.version && strcmp (mi.version, ABI_BUILD_VERSION) == 0, "XAP_ModuleInfo.version == 3.0.8");
	CHECK (mi.author && mi.author[0], "XAP_ModuleInfo.author filled");

	/* ---- 3. supports_version ---- */
	CHECK (ver (3, 0, 8) == 1, "abi_plugin_supports_version(3,0,8) == 1");
	CHECK (ver (1, 2, 3) == 1, "abi_plugin_supports_version(any) == 1");

	/* ---- 4. EditMethod container holds "Wikipedia_invoke" ---- */
	XAP_App * app = XAP_App::getApp ();
	EV_EditMethodContainer * pEMC = app->getEditMethodContainer ();
	CHECK (pEMC != 0, "getEditMethodContainer() != 0");

	EV_EditMethod * em = pEMC->findEditMethodByName ("Wikipedia_invoke");
	CHECK (em != 0, "EditMethod 'Wikipedia_invoke' registered in container");
	CHECK (em && strcmp (em->getName (), "Wikipedia_invoke") == 0, "EditMethod name matches");
	CHECK (pEMC->countEditMethods () >= 1, "container has >= 1 edit method");

	EV_EditMethod * em2 = ev_EditMethod_lookup ("Wikipedia_invoke");
	CHECK (em2 == em && em2 != 0, "ev_EditMethod_lookup('Wikipedia_invoke') hits");
	CHECK (ev_EditMethod_lookup ("NoSuchMethod") == 0, "ev_EditMethod_lookup(unknown) == 0");

	/* ---- 5. menu factory / action set ---- */
	XAP_Menu_Factory * pFact = app->getMenuFactory ();
	CHECK (pFact != 0, "getMenuFactory() != 0");
	CHECK (pFact->hasLabel ("Wi&ki Encyclopedia"), "menu label 'Wi&ki Encyclopedia' added");

	XAP_Menu_Id menuID = pFact->getIDForLabel ("Wi&ki Encyclopedia");
	CHECK (menuID != 0, "menu label has a valid id");

	EV_Menu_ActionSet * pActionSet = app->getMenuActionSet ();
	const EV_Menu_Action * action = pActionSet ? pActionSet->getAction (menuID) : 0;
	CHECK (action != 0, "action for 'Wi&ki Encyclopedia' id in action set");
	CHECK (action && action->getMethodName () &&
	       strcmp (action->getMethodName (), "Wikipedia_invoke") == 0,
	       "action bound to 'Wikipedia_invoke'");

	/* ---- 6. end-to-end invoke: selected word drives openURL ---- */
	XAP_Frame * pFrame = app->getLastFocussedFrame ();
	CHECK (pFrame != 0, "getLastFocussedFrame() returns a frame");
	FV_View * pView = pFrame ? static_cast<FV_View *> (pFrame->getCurrentView ()) : 0;
	CHECK (pView != 0, "frame->getCurrentView() returns an FV_View");

	if (em && pView) {
		static const UT_UCS4Char WORD[] = { 'w','a','r', 0 };
		pView->setSelectionText (WORD);
		CHECK (!pView->isSelectionEmpty (), "selection not empty after setSelectionText");

		bool ok = em->Fn (pView, 0);
		CHECK (ok == true, "Wikipedia_invoke returns true");

		const char * url = app->getLastOpenedURL ();
		CHECK (url && strstr (url, "w/wiki.phtml?search=war") != 0,
		       "openURL called with 'w/wiki.phtml?search=war'");
		CHECK (url && strstr (url, "&go=Go") != 0, "openURL URL carries '&go=Go'");

		/* empty selection → base URL, no search string */
		static const UT_UCS4Char EMPTY[] = { 0 };
		pView->setSelectionText (EMPTY);
		CHECK (pView->isSelectionEmpty (), "selection empty after clearing");
		ok = em->Fn (pView, 0);
		CHECK (ok == true, "Wikipedia_invoke (empty selection) returns true");
		CHECK (strcmp (app->getLastOpenedURL (), "http://www.wikipedia.com/") == 0,
		       "openURL called with base URL when nothing selected");
	}

	/* ---- 7. unregister: container + menu must be cleaned up ---- */
	int ur = unreg (&mi);
	CHECK (ur == 1, "abi_plugin_unregister() returns 1");
	CHECK (mi.name == 0 && mi.desc == 0, "XAP_ModuleInfo cleared after unregister");
	CHECK (pEMC->findEditMethodByName ("Wikipedia_invoke") == 0,
	       "EditMethod 'Wikipedia_invoke' removed after unregister");
	CHECK (!pFact->hasLabel ("Wi&ki Encyclopedia"),
	       "menu label 'Wi&ki Encyclopedia' removed after unregister");

	dlclose (handle);

	if (failures == 0) {
		printf ("PASS: abiword-plugin-wikipedia end-to-end test succeeded (%d/%d checks)\n",
		        checks - failures, checks);
		return 0;
	}
	printf ("FAIL: %d/%d checks failed\n", failures, checks);
	return 1;
}
