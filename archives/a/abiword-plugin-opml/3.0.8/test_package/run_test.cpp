/* test_package/run_test.cpp — consumer test for abiword-plugin-opml.
 *
 * Verifies the installed plugin module can be dlopen'ed and that its
 * exported ABI (abi_plugin_supports_version / abi_plugin_register /
 * abi_plugin_unregister) works against the real XAP_ModuleInfo struct.
 */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>

typedef struct {
	const char * name;
	const char * desc;
	const char * version;
	const char * author;
	const char * usage;
} XAP_ModuleInfo;

typedef int (*reg_fn) (XAP_ModuleInfo * mi);
typedef int (*ver_fn) (unsigned int major, unsigned int minor, unsigned int release);

int main (int argc, char ** argv)
{
	if (argc < 2) {
		fprintf (stderr, "usage: %s <path-to-libabiword-plugin-opml.so>\n", argv[0]);
		return 1;
	}

	void * handle = dlopen (argv[1], RTLD_NOW | RTLD_LOCAL);
	if (!handle) {
		fprintf (stderr, "dlopen failed: %s\n", dlerror ());
		return 1;
	}

	ver_fn supports = (ver_fn)dlsym (handle, "abi_plugin_supports_version");
	reg_fn reg      = (reg_fn)dlsym (handle, "abi_plugin_register");
	reg_fn unreg    = (reg_fn)dlsym (handle, "abi_plugin_unregister");
	if (!supports || !reg || !unreg) {
		fprintf (stderr, "dlsym failed: %s\n", dlerror ());
		dlclose (handle);
		return 1;
	}

	if (!supports (3, 0, 8)) {
		fprintf (stderr, "abi_plugin_supports_version(3,0,8) returned 0\n");
		dlclose (handle);
		return 1;
	}

	XAP_ModuleInfo mi;
	memset (&mi, 0, sizeof (mi));
	if (reg (&mi) != 1) {
		fprintf (stderr, "abi_plugin_register failed\n");
		dlclose (handle);
		return 1;
	}
	if (!mi.name || strcmp (mi.name, "OPML Importer") != 0) {
		fprintf (stderr, "unexpected module name: %s\n", mi.name ? mi.name : "()");
		dlclose (handle);
		return 1;
	}
	if (unreg (&mi) != 1) {
		fprintf (stderr, "abi_plugin_unregister failed\n");
		dlclose (handle);
		return 1;
	}

	dlclose (handle);
	printf ("PASS: abiword-plugin-opml module loaded, registered and unregistered\n");
	return 0;
}
