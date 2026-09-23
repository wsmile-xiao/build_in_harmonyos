/*
 * Consumer test for libnfsidmap-ldap/2.6.4.
 *
 * It exercises the package the way a consumer does:
 *   1. link against libnfsidmap.so.1 and call its public API
 *      (nfs4_set_debug / nfs4_init_name_mapping / nfs4_term_name_mapping);
 *   2. let libnfsidmap load the LDAP mapping plugin named in idmapd.conf
 *      ("Method = umich_ldap") through the plugin search path;
 *   3. dlopen the plugin directly and verify the plugin ABI hook
 *      (libnfsidmap_plugin_init -> struct trans_func) is exported.
 *
 * No LDAP server is contacted: umichldap_init() only reads its
 * [UMICH_SCHEMA] configuration, which is what makes this an offline test.
 */
#include <sys/types.h>

#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <nfsidmap.h>
#include <nfsidmap_plugin.h>

static int failures;

static void check(int ok, const char *what)
{
	printf("%s: %s\n", ok ? "PASS" : "FAIL", what);
	if (!ok)
		failures++;
}

int main(int argc, char **argv)
{
	int rc;
	void *dl;
	struct trans_func *(*plugin_init)(void);

	if (argc != 2) {
		fprintf(stderr, "usage: %s <idmapd.conf>\n", argv[0]);
		return 2;
	}

	nfs4_set_debug(3, NULL);

	/* 1. public API: parse the config and load the requested method plugin */
	rc = nfs4_init_name_mapping(argv[1]);
	check(rc == 0, "nfs4_init_name_mapping() loads the umich_ldap plugin");

	/* 2. plugin ABI: the plugin can be dlopen()ed by name and exports the
	 *    initialization hook that libnfsidmap looks up. */
	dl = dlopen("umich_ldap.so", RTLD_NOW | RTLD_LOCAL);
	if (dl == NULL) {
		printf("dlopen(umich_ldap.so): %s\n", dlerror());
		check(0, "dlopen(\"umich_ldap.so\")");
	} else {
		check(1, "dlopen(\"umich_ldap.so\")");
		plugin_init = (struct trans_func *(*)(void))
			dlsym(dl, "libnfsidmap_plugin_init");
		check(plugin_init != NULL,
		      "plugin exports libnfsidmap_plugin_init()");
		if (plugin_init != NULL) {
			struct trans_func *tf = plugin_init();
			check(tf != NULL && tf->name != NULL &&
			      strcmp(tf->name, "umich_ldap") == 0,
			      "plugin vtable reports the method name umich_ldap");
		}
		dlclose(dl);
	}

	nfs4_term_name_mapping();

	printf("%s (%d assertion(s) failed)\n", failures ? "FAIL" : "PASS",
	       failures);
	return failures ? 1 : 0;
}
