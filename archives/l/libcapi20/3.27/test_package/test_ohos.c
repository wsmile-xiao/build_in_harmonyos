/*
 * HarmonyOS specific tests for libcapi20 3.27.
 *
 * The cases below verify the parts of the adaptation that are platform specific
 * rather than plain API behaviour:
 *
 *   - the CAPI driver of this library is implemented as a set of dlopen()-ed
 *     libtool plugin modules; on HarmonyOS the platform loader has to relocate
 *     and bind them from the package directory (no /usr/lib, HMDFS path limits,
 *     sealed/unsealed ELF rules),
 *   - the module directory of the packaged library is no longer the compile time
 *     absolute LIBDIR, it is relocated through CAPI20_MODULE_DIR (adaptation
 *     patch 0003), and the plugins really end up mapped into the process.
 *
 * The test therefore inspects the loaded objects of its own process through
 * /proc/self/maps, which is the authoritative view of what the HarmonyOS loader
 * actually mapped.
 */
#include <dlfcn.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include <capi20.h>

static int g_total;
static int g_failed;

static void check(int ok, const char *name)
{
	g_total++;
	if (ok) {
		printf("PASS %s\n", name);
	} else {
		g_failed++;
		printf("FAIL %s\n", name);
	}
}

static const char *env_or_empty(const char *key)
{
	const char *value = getenv(key);

	return value != NULL ? value : "";
}

/* Returns 1 when needle appears in the mapped object list of this process. */
static int mapped_object(const char *needle)
{
	FILE *maps;
	char line[1024];
	int found = 0;

	maps = fopen("/proc/self/maps", "r");
	if (maps == NULL) {
		return -1;
	}
	while (fgets(line, sizeof(line), maps) != NULL) {
		if (strstr(line, needle) != NULL) {
			found = 1;
			break;
		}
	}
	fclose(maps);

	return found;
}

static void *open_object(const char *path)
{
	void *handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);

	if (handle == NULL) {
		printf("  dlopen(%s) failed: %s\n", path, dlerror());
	}
	return handle;
}

/* Case 1: the package module directory is honoured by the library, i.e. the
 *         libraries' own module loading reaches the plugins through the loader.
 *
 *         /proc/self/maps resolves HarmonyOS files through their HMDFS backing
 *         path, so the mapped objects are matched by base name.  No plugin is
 *         opened by the test before this case. */
#define PLUGIN_MARKER "lib_capi_mod_"

static void case_module_dir_override(void)
{
	const char *module_dir = env_or_empty("CAPI20_MODULE_DIR");
	unsigned rc;
	int before;
	int after;

	before = mapped_object(PLUGIN_MARKER);
	rc = capi20_isinstalled();
	after = mapped_object(PLUGIN_MARKER);

	printf("  module dir: %s (isinstalled=0x%04x, plugins mapped: %d -> %d)\n",
	       module_dir, rc, before, after);

	/* No CAPI device exists on HarmonyOS, so the call must fail cleanly ... */
	check(rc == CapiRegNotInstalled,
	      "ohos_module_dir_override_reports_not_installed");
	/* ... but the library must have mapped the plugins from its module dir. */
	check(before == 0 && after == 1, "ohos_module_dir_override_loads_plugins");
}

/* Case 2: the core shared object of the package is loadable on HarmonyOS. */
static void case_core_library(void)
{
	const char *libdir = env_or_empty("CAPI_TEST_LIBDIR");
	char path[1024];
	void *handle;

	if (libdir[0] == '\0') {
		check(0, "ohos_core_library_loads");
		return;
	}

	snprintf(path, sizeof(path), "%s/libcapi20.so.3", libdir);
	handle = open_object(path);
	check(handle != NULL && dlsym(handle, "capi20_isinstalled") != NULL,
	      "ohos_core_library_loads");
	if (handle != NULL) {
		dlclose(handle);
	}
}

/* Case 3: every plugin module the library ships is loadable and exports the
 *         module entry point the library resolves with dlsym(). */
static void case_plugin_modules(void)
{
	static const char *const modules[] = {
		"lib_capi_mod_std",
		"lib_capi_mod_fritzbox",
		"lib_capi_mod_rcapi",
	};
	const char *module_dir = env_or_empty("CAPI20_MODULE_DIR");
	char path[1024];
	void *handle;
	int i;
	int ok = 1;

	if (module_dir[0] == '\0') {
		check(0, "ohos_plugin_modules_load");
		return;
	}

	for (i = 0; i < (int)(sizeof(modules) / sizeof(modules[0])); i++) {
		snprintf(path, sizeof(path), "%s/%s.so", module_dir, modules[i]);
		handle = open_object(path);
		if (handle == NULL) {
			ok = 0;
			continue;
		}
		if (dlsym(handle, "InitModule") == NULL) {
			printf("  InitModule missing in %s: %s\n", path, dlerror());
			ok = 0;
		}
	}

	check(ok, "ohos_plugin_modules_load");
}

int main(void)
{
	printf("libcapi20 HarmonyOS platform tests\n");

	/* Runs first: it observes the loader state produced by the library itself. */
	case_module_dir_override();
	case_core_library();
	case_plugin_modules();

	printf("assertions: %d/%d passed\n", g_total - g_failed, g_total);
	return g_failed == 0 ? 0 : 1;
}
