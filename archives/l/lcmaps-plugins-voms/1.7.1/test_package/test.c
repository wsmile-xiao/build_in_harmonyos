/*
 * lcmaps-plugins-voms 1.7.1 test_package — OHOS (aarch64/musl) consumer smoke
 * test.
 *
 * Exercises the consumption mode used by the LCMAPS framework (dlopen of the
 * plugin .so followed by dlsym of the plugin entry points):
 *
 *  1. musl dynamic loading (OHOS adaptation, knowledge E013): dlopen/dlsym/
 *     dlclose must work on the packaged plugin objects. Every plugin exports
 *     plugin_initialize / plugin_introspect / plugin_run / plugin_terminate /
 *     plugin_verify (verified with llvm-nm on the build).
 *  2. Package layout: the six plugins live in lib/lcmaps/ together with the
 *     lcmaps_*.mod symlink aliases the LCMAPS plugin manager resolves.
 *
 * Upstream ships no automated tests (see test_package/MANIFEST.yml), so this
 * smoke test is the verification vehicle.
 *
 * Usage: test_lcmaps_plugins_voms <package_root>
 *
 * The test binary links liblcmaps_without_gsi directly (NEEDED), reproducing
 * the LCMAPS evaluation engine's process image: the framework (lcmaps_log
 * and friends) is already loaded when the plugins get dlopen()ed.
 *
 * E046 note: HMDFS refuses to dlopen unsigned ELF objects with EPERM. When
 * a plugin dlopen fails with EPERM the run is treated as SKIP
 * (device-only limitation; same precedent as the lcmaps/autofs test packages).
 */
#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>

typedef int (*plugin_entry_t)(void);

static int check_file(const char *root, const char *rel, const char *what)
{
	char buf[1024];
	struct stat st;
	int ok;

	snprintf(buf, sizeof(buf), "%s/%s", root, rel);
	ok = stat(buf, &st) == 0;
	printf("%s: %s (%s)\n", ok ? "PASS" : "FAIL", what, buf);
	return ok ? 0 : 1;
}

static int try_dlsym(void *handle, const char *name)
{
	void *sym;

	dlerror(); /* clear pending error */
	sym = dlsym(handle, name);
	if (sym == NULL) {
		const char *err = dlerror();
		printf("FAIL: dlsym(%s): %s\n", name, err ? err : "symbol is NULL");
		return 1;
	}
	printf("PASS: dlsym(%s) -> %p\n", name, sym);
	return 0;
}

/* dlopen one plugin and resolve its entry points. Returns 0 on success,
 * 1 on failure, 2 on the E046 unsigned-ELF SKIP case. */
static int probe_plugin(const char *root, const char *file)
{
	char path[1024];
	void *handle;
	int rc = 0;

	snprintf(path, sizeof(path), "%s/lib/lcmaps/%s", root, file);
	dlerror();
	handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
	if (handle == NULL) {
		const char *err = dlerror();
		if (err && strstr(err, "Permission denied")) {
			printf("SKIP: dlopen(%s): %s (E046: unsigned ELF on HMDFS)\n",
			       path, err);
			return 2;
		}
		printf("FAIL: dlopen(%s): %s\n", path, err ? err : "unknown");
		return 1;
	}
	printf("PASS: dlopen(%s)\n", path);

	rc |= try_dlsym(handle, "plugin_initialize");
	rc |= try_dlsym(handle, "plugin_run");
	rc |= try_dlsym(handle, "plugin_terminate");

	dlclose(handle);
	return rc;
}

int main(int argc, char **argv)
{
	static const char *plugins[] = {
		"liblcmaps_voms.so",
		"liblcmaps_ban_fqan.so",
		"liblcmaps_voms_localaccount.so",
		"liblcmaps_voms_poolaccount.so",
		"liblcmaps_voms_localgroup.so",
		"liblcmaps_voms_poolgroup.so",
	};
	const char *root;
	int failures = 0;
	int skips = 0;
	size_t i;

	if (argc < 2) {
		fprintf(stderr, "usage: %s <package_root>\n", argv[0]);
		return 2;
	}
	root = argv[1];

	/* Package layout assertions. */
	failures += check_file(root, "lib/lcmaps/liblcmaps_voms.so",
			       "plugin object installed");
	for (i = 0; i < sizeof(plugins) / sizeof(plugins[0]); i++) {
		char rel[128];

		snprintf(rel, sizeof(rel), "lib/lcmaps/%s", plugins[i]);
		failures += check_file(root, rel, "plugin object");
		/* lcmaps_<name>.mod symlink alias pairs with every plugin:
		 * liblcmaps_<x>.so -> strip "lib" prefix, swap ".so" for ".mod". */
		{
			char alias[128];
			char *so;
			snprintf(alias, sizeof(alias), "lib/lcmaps/%s", plugins[i] + 3);
			so = strstr(alias, ".so");
			if (so)
				strcpy(so, ".mod");
			failures += check_file(root, alias, "plugin .mod alias");
		}
	}

	/* dlopen/dlsym exercise of every plugin (the LCMAPS consumption mode). */
	for (i = 0; i < sizeof(plugins) / sizeof(plugins[0]); i++) {
		int r = probe_plugin(root, plugins[i]);
		if (r == 1)
			failures++;
		else if (r == 2)
			skips++;
	}

	if (failures) {
		printf("RESULT: FAIL (%d failure(s), %d skip(s))\n", failures, skips);
		return 1;
	}
	printf("RESULT: PASS (%d skip(s) allowed)\n", skips);
	return 0;
}
