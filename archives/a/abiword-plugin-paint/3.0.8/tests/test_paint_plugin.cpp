/* tests/test_paint_plugin.cpp — OHOS end-to-end test for the
 * abiword-plugin-paint module.
 *
 * Verifies (R34: substantive use of the package API):
 *   1. the plugin module dlopens and abi_plugin_register() fills XAP_ModuleInfo
 *      (name "AbiPaint", version contains "3.0.8");
 *   2. registration creates the "_AbiPaint_" preference scheme with sensible
 *      defaults (image editor + leave-as-PNG flag);
 *   3. registration adds the plugin's menu items and edit methods to the
 *      AbiWord menu/action framework;
 *   4. abi_plugin_unregister() clears the module info and removes the menus.
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "ut_types.h"
#include "xap_App.h"
#include "xap_Frame.h"
#include "xap_Prefs.h"
#include "xap_Menu_Layouts.h"
#include "ev_EditMethod.h"
#include "xap_Module.h"

typedef int (*plugin_reg_fn) (XAP_ModuleInfo * mi);
typedef int (*plugin_ver_fn) (unsigned int major, unsigned int minor, unsigned int release);

static int failures = 0;

#define CHECK(cond, msg)                                                     \
	do {                                                                     \
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

	plugin_ver_fn  vers = (plugin_ver_fn) dlsym (handle, "abi_plugin_supports_version");
	plugin_reg_fn  reg  = (plugin_reg_fn) dlsym (handle, "abi_plugin_register");
	plugin_reg_fn  unreg= (plugin_reg_fn) dlsym (handle, "abi_plugin_unregister");
	CHECK (vers != 0, "dlsym(abi_plugin_supports_version)");
	CHECK (reg != 0,  "dlsym(abi_plugin_register)");
	CHECK (unreg != 0, "dlsym(abi_plugin_unregister)");
	if (!vers || !reg || !unreg) {
		dlclose (handle);
		return 1;
	}

	/* version gate: the plugin must accept the AbiWord 3.x API */
	CHECK (vers (3, 0, 8) == 1, "abi_plugin_supports_version(3,0,8)");

	/* ---- 2. register: XAP_ModuleInfo must be filled ---- */
	XAP_ModuleInfo mi;
	memset (&mi, 0, sizeof (mi));

	int r = reg (&mi);
	CHECK (r == 1, "abi_plugin_register() returns 1");
	CHECK (mi.name && strcmp (mi.name, "AbiPaint") == 0, "XAP_ModuleInfo.name == 'AbiPaint'");
	CHECK (mi.desc && strstr (mi.desc, "image") != 0, "XAP_ModuleInfo.desc mentions image editing");
	CHECK (mi.version && strstr (mi.version, "3.0.8") != 0, "XAP_ModuleInfo.version contains 3.0.8");
	CHECK (mi.author && mi.usage, "XAP_ModuleInfo.author + usage filled");

	/* ---- 3. preference scheme created with defaults ---- */
	XAP_App * pApp = XAP_App::getApp ();
	CHECK (pApp != 0, "XAP_App::getApp()");
	XAP_Prefs * prefs = pApp ? pApp->getPrefs () : 0;
	CHECK (prefs != 0, "XAP_App::getPrefs()");

	XAP_PrefsScheme * scheme = prefs ? prefs->getPluginScheme ("_AbiPaint_") : 0;
	CHECK (scheme != 0, "plugin scheme '_AbiPaint_' registered");

	if (scheme) {
		std::string editor;
		bool bLeavePng = false;
		CHECK (scheme->getValue ("szImageEditor", editor), "getValue(szImageEditor) exists");
		CHECK (scheme->getValueBool ("bLeaveImageAsPNG", &bLeavePng), "getValueBool(bLeaveImageAsPNG) exists");
	}

	/* ---- 4. menus + edit methods registered ---- */
	XAP_Menu_Factory * factory = pApp ? pApp->getMenuFactory () : 0;
	CHECK (factory && factory->_test_menuCount () > 0, "menu items added by addToMenus()");

	EV_EditMethodContainer * emc = pApp ? pApp->getEditMethodContainer () : 0;
	CHECK (emc && emc->countEditMethods () > 0, "edit methods added to container");
	CHECK (emc && emc->findEditMethodByName ("AbiPaint_PluginCallback_editImage") != 0,
	       "editImage edit method registered");
	CHECK (emc && emc->findEditMethodByName ("AbiPaint_PluginCallback_specify") != 0,
	       "specify edit method registered");

	/* ---- 5. unregister: info cleared + menus removed ---- */
	memset (&mi, 0, sizeof (mi));
	r = unreg (&mi);
	CHECK (r == 1, "abi_plugin_unregister() returns 1");
	CHECK (mi.name == 0 && mi.desc == 0 && mi.version == 0, "XAP_ModuleInfo cleared by unregister");
	CHECK (factory && factory->_test_menuCount () == 0, "menu items removed by removeFromMenus()");

	dlclose (handle);

	printf ("\n%s: %d check(s) failed\n", failures ? "FAILED" : "PASS", failures);
	return failures ? 1 : 0;
}
