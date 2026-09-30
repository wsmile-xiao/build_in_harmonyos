/*
 * lcmaps-plugins-basic 1.7.1 test_package — OHOS (aarch64/musl) consumer smoke test.
 *
 * Verifies the packaged plugin artifacts and exercises the platform
 * adaptation points introduced by this port:
 *
 *  1. musl dynamic loading (OHOS adaptation, knowledge E013): the dl* API is
 *     provided by libc. The LCMAPS framework consumes these plugins by
 *     dlopen()ing the installed <libdir>/lcmaps/lcmaps_<mod>.mod files, and
 *     the plugins carry undefined lcmaps_* references that must resolve
 *     against the framework. Real consumers link the framework as a startup
 *     dependency (musl global symbol scope); this test does the same
 *     (CMakeLists links liblcmaps_without_gsi.so) because musl does NOT add
 *     dlopen(RTLD_GLOBAL) objects to the relocation scope of objects loaded
 *     later (CI run5 finding). The test dlopen()s each of the 7 installed
 *     .mod entries by their official install name (exercises the
 *     install-data-hook symlink/copy fallback, patch 0004 / knowledge E018,
 *     and the OHOS-specific artifact layout lib/lcmaps/) with RTLD_NOW —
 *     proving the full cross-library symbol closure resolves.
 *  2. Plugin entry surface: each module must export plugin_initialize,
 *     plugin_run and plugin_terminate (the LCMAPS plugin contract that the
 *     framework dlsym()s).
 *  3. Packaged artifact manifest: 7 .so modules + 7 .mod install entries
 *     under lib/lcmaps/, man8 pages installed.
 *
 * Usage: test_lcmaps_plugins_basic <package_root>
 */
#include <dlfcn.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>

static const char *const g_mods[7] = {
	"dummy_bad", "dummy_good", "ban_dn",
	"localaccount", "poolaccount", "posix_enf", "ldap_enf"
};

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
		printf("FAIL: dlsym(%s): %s\n", name,
		       err ? err : "symbol is NULL");
		return 1;
	}
	printf("PASS: dlsym(%s) -> %p\n", name, sym);
	return 0;
}

int main(int argc, char *argv[])
{
	const char *root;
	const char *fw_root;
	char path[1024];
	void *fw;
	int rc = 0;
	size_t i;

	if (argc < 3) {
		fprintf(stderr, "usage: test_lcmaps_plugins_basic "
				"<plugins_package_root> <lcmaps_framework_root>\n");
		return 2;
	}
	root = argv[1];
	fw_root = argv[2];

	/* 1. packaged artifact manifest: 7 modules + 7 .mod install entries */
	for (i = 0; i < sizeof(g_mods) / sizeof(g_mods[0]); i++) {
		snprintf(path, sizeof(path), "lib/lcmaps/liblcmaps_%s.so",
			 g_mods[i]);
		rc |= check_file(root, path, "plugin module .so");
		snprintf(path, sizeof(path), "lib/lcmaps/lcmaps_%s.mod",
			 g_mods[i]);
		rc |= check_file(root, path, "plugin install entry .mod");
	}
	rc |= check_file(root, "share/man/man8/lcmaps_localaccount.mod.8",
			 "man8 page");

	/* 2. runtime: preload the framework RTLD_GLOBAL — plugin modules carry
	 * undefined lcmaps_* references (lcmaps_log, credential helpers) and
	 * dlsym(RTLD_DEFAULT, "lcmaps_get_major_version") probes that must
	 * resolve against the framework (musl dlopen adaptation, E013/E004).
	 * The framework lives in the lcmaps dependency package, not in the
	 * plugins package (plugins are dlopen-only, no link interface). */
	snprintf(path, sizeof(path), "%s/lib/liblcmaps_without_gsi.so", fw_root);
	dlerror();
	fw = dlopen(path, RTLD_NOW | RTLD_GLOBAL);
	if (fw == NULL) {
		const char *err = dlerror();
		if (err && strstr(err, "Permission denied")) {
			/* OHOS HMDFS refuses unsigned ELF (E046): platform
			 * limitation, not a packaging failure. */
			printf("SKIP: dlopen %s — unsigned ELF (%s)\n", path,
			       err);
			return rc;
		}
		printf("FAIL: dlopen framework %s: %s\n", path,
		       err ? err : "?");
		return 1;
	}
	printf("PASS: dlopen framework %s (RTLD_GLOBAL)\n", path);
	rc |= try_dlsym(fw, "lcmaps_get_major_version");
	rc |= try_dlsym(fw, "lcmaps_log");

	/* 3. each plugin via its installed .mod name (framework consumption
	 * mode) + dlsym of the three plugin entry points */
	for (i = 0; i < sizeof(g_mods) / sizeof(g_mods[0]); i++) {
		char mod[256];
		void *handle;

		snprintf(mod, sizeof(mod), "lcmaps_%s", g_mods[i]);
		snprintf(path, sizeof(path), "%s/lib/lcmaps/%s.mod", root, mod);
		dlerror();
		handle = dlopen(path, RTLD_NOW | RTLD_LOCAL);
		if (handle == NULL) {
			const char *err = dlerror();
			printf("FAIL: dlopen %s: %s\n", path, err ? err : "?");
			rc |= 1;
			continue;
		}
		printf("PASS: dlopen %s\n", path);
		rc |= try_dlsym(handle, "plugin_initialize");
		rc |= try_dlsym(handle, "plugin_run");
		rc |= try_dlsym(handle, "plugin_terminate");
		dlclose(handle);
	}
	dlclose(fw);

	if (rc == 0)
		printf("All lcmaps-plugins-basic smoke tests PASSED\n");
	else
		printf("lcmaps-plugins-basic smoke tests FAILED (%d)\n", rc);
	return rc;
}
