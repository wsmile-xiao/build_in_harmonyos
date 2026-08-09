/* test_package/run_test.cpp — consumer test for abiword-plugin-clarisworks.
 *
 * Substantively exercises the installed package (R34): dlopens the plugin
 * module, calls its exported abi_plugin_register / abi_plugin_unregister /
 * abi_plugin_supports_version ABI, and verifies the filled XAP_ModuleInfo.
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

extern "C" {
	typedef struct {
		const char * name;
		const char * desc;
		const char * version;
		const char * author;
		const char * usage;
	} XAP_ModuleInfo;
}

typedef int (*plugin_reg_fn) (XAP_ModuleInfo * mi);
typedef int (*plugin_ver_fn) (unsigned int major, unsigned int minor, unsigned int release);

int main (int argc, char ** argv)
{
	if (argc < 2) {
		fprintf (stderr, "usage: %s <path-to-libabiword-plugin-clarisworks.so>\n", argv[0]);
		return 2;
	}
	const char * so = argv[1];

	void * handle = dlopen (so, RTLD_NOW | RTLD_LOCAL);
	if (!handle) {
		fprintf (stderr, "FAIL dlopen(%s): %s\n", so, dlerror ());
		return 1;
	}

	plugin_reg_fn reg   = (plugin_reg_fn)dlsym (handle, "abi_plugin_register");
	plugin_reg_fn unreg = (plugin_reg_fn)dlsym (handle, "abi_plugin_unregister");
	plugin_ver_fn  vers = (plugin_ver_fn) dlsym (handle, "abi_plugin_supports_version");
	if (!reg || !unreg || !vers) {
		fprintf (stderr, "FAIL dlsym abi_plugin_*: %s\n", dlerror ());
		goto out_close;
	}

	/* version gate: the plugin must accept the AbiWord 3.x API */
	if (vers (3, 0, 0) != 1) {
		fprintf (stderr, "FAIL abi_plugin_supports_version(3,0,0)\n");
		goto out_close;
	}

	XAP_ModuleInfo mi;
	memset (&mi, 0, sizeof (mi));

	if (reg (&mi) != 1) {
		fprintf (stderr, "FAIL abi_plugin_register\n");
		goto out_close;
	}
	if (!mi.name || !mi.desc || !mi.author || !mi.usage || !mi.version) {
		fprintf (stderr, "FAIL XAP_ModuleInfo fields not filled\n");
		goto out_unreg;
	}
	if (strcmp (mi.version, "3.0.8") != 0) {
		fprintf (stderr, "FAIL XAP_ModuleInfo.version = '%s' (expected 3.0.8)\n",
		         mi.version ? mi.version : "(null)");
		goto out_unreg;
	}

	/* capture the info before unloading the module (the pointers live in
	 * the .so data segment and are dangling after dlclose) */
	printf ("PASS: abiword-plugin-clarisworks module loaded, registered and unregistered "
	        "(%s / %s)\n", mi.name ? mi.name : "?", mi.version ? mi.version : "?");

	if (unreg (&mi) != 1) {
		fprintf (stderr, "FAIL abi_plugin_unregister\n");
		goto out_close;
	}

	dlclose (handle);
	return 0;

out_unreg:
	/* revoke the registration before unloading so the importer registry
	 * does not keep a dangling pointer to the module's sniffer */
	unreg (&mi);
out_close:
	dlclose (handle);
	return 1;
}
