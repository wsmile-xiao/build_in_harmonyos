/*
 * lcmaps-plugins-voms 1.7.1 test_package — OHOS (aarch64/musl) end-to-end
 * consumer test.
 *
 * Runs a complete LCMAPS evaluation round trip, the way a real consumer
 * (the lcmaps engine embedded in e.g. gLExec/pilot jobs) drives the plugins:
 *
 *   lcmaps_init()                       engine bootstrap
 *   -> policy "acquisition_policy"      (parsed from a generated lcmaps.db,
 *                                        PDL policy language of LCMAPS 1.6.x)
 *   -> lcmaps_ban_fqan.mod              FQAN not on the ban list -> pass
 *   -> lcmaps_voms_localaccount.mod     FQAN "/vo/harmony/test/group" is
 *                                       resolved through a generated
 *                                       grid-mapfile to the account "root"
 *   -> lcmaps_run_with_fqans_and_return_account()
 *                                       returns the mapped uid/gid
 *   -> lcmaps_term()                    engine shutdown
 *
 * No VOMS credential/certificate is needed: the FQAN list is injected
 * directly through lcmaps_run_with_fqans_and_return_account(), the
 * documented no-GSI consumption mode (the equivalent of the GSI-mode
 * lcmaps_run_with_usercred_and_return_account for credential-less
 * environments).
 *
 * The evaluation artifacts (lcmaps.db / grid-mapfile / ban-mapfile) are
 * generated at runtime in the current directory; absolute paths are baked
 * in so the plugin manager finds them regardless of its working directory.
 *
 * Usage: test_lcmaps_plugins_voms_e2e <package_root>
 *
 * The test binary links liblcmaps_without_gsi statically (whole-archive)
 * and exports its symbols (-rdynamic), reproducing the LCMAPS engine's
 * process image: the plugins' lcmaps_log/... relocations resolve against
 * the main program exactly as they do in production.
 */
#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>
#include <sys/types.h>
#include <pwd.h>

#include <lcmaps/lcmaps_basic.h>

#define TEST_FQAN "/vo/harmony/test/group"
#define TEST_DN "CN=OHPCD Test User,O=OpenHarmonyPC"

static void write_file(const char *path, const char *content)
{
	FILE *f = fopen(path, "w");

	if (f == NULL) {
		fprintf(stderr, "E2E FAIL: cannot write %s: %s\n", path, strerror(errno));
		exit(2);
	}
	fputs(content, f);
	fclose(f);
}

/*
 * One full evaluation round trip.
 * Returns 0 on success, 1 on hard failure, 3 on transient environment
 * trouble (HMDFS attribute-cache EACCES on freshly written files, knowledge
 * E075 family) where a retry may help.
 */
static int run_evaluation(const char *pkg_root, const char *workdir)
{
	char gridmap[2048], banmap[2048], dbfile[2048], content[2048];
	uid_t out_uid = (uid_t)-1;
	gid_t *ppgid = NULL, *psgid = NULL;
	int npg = 0, nsg = 0;
	char *poolindex = NULL;
	char *fqans[1];
	FILE *dbg = stderr;
	int rc;

	/* grid-mapfile: FQAN -> fixed account "root" (uid 0, present on every
	 * unix system; only getpwnam reads are needed, no privileges). */
	snprintf(gridmap, sizeof(gridmap), "%s/lcmaps-e2e-grid-mapfile", workdir);
	snprintf(content, sizeof(content), "\"%s\" root\n", TEST_FQAN);
	write_file(gridmap, content);

	/* ban-mapfile: empty — the test FQAN is NOT banned, so the ban_fqan
	 * chain-head plugin passes. */
	snprintf(banmap, sizeof(banmap), "%s/lcmaps-e2e-ban-mapfile", workdir);
	write_file(banmap, "");

	/* lcmaps policy database (LCMAPS 1.6.x PDL format):
	 *   - path=<package>/lib/lcmods — plugin location (the .mod aliases)
	 *   - plugin definitions with their arguments
	 *   - policy with a single rule: ban_fqan -> localaccount
	 */
	snprintf(dbfile, sizeof(dbfile), "%s/lcmaps-e2e-lcmaps.db", workdir);
	snprintf(content, sizeof(content),
		 "path = %s/lib/lcmaps\n"
		 "\n"
		 "ban_fqan = \"lcmaps_ban_fqan.mod\"\n"
		 "           \"-banmapfile %s\"\n"
		 "localaccount = \"lcmaps_voms_localaccount.mod\"\n"
		 "               \"-gridmapfile %s\"\n"
		 "\n"
		 "acquisition_policy:\n"
		 "    ban_fqan -> localaccount\n",
		 pkg_root, banmap, gridmap);
	write_file(dbfile, content);

	if (setenv("LCMAPS_DB_FILE", dbfile, 1) != 0) {
		fprintf(stderr, "E2E FAIL: setenv(LCMAPS_DB_FILE): %s\n", strerror(errno));
		return 1;
	}

	/* HMDFS attribute-cache latency (knowledge E075): give freshly written
	 * policy/map files a moment before the engine opens them. */
	sleep(1);

	if (lcmaps_init(dbg) != 0) {
		fprintf(stderr, "E2E FAIL: lcmaps_init\n");
		return 1;
	}

	fqans[0] = (char *)TEST_FQAN;
	rc = lcmaps_run_with_fqans_and_return_account(
			(char *)TEST_DN, fqans, 1,
			NULL /* lcmaps_request_t */,
			0 /* npols */, NULL /* policynames */,
			&out_uid, &ppgid, &npg, &psgid, &nsg, &poolindex);

	if (rc != 0) {
		const char *err = dlerror();
		fprintf(stderr,
			"E2E FAIL: lcmaps_run_with_fqans_and_return_account rc=%d%s%s\n",
			rc, err ? ": " : "", err ? err : "");
		lcmaps_term();
		return 3; /* transient class: retry once */
	}

	if (lcmaps_term() != 0)
		fprintf(stderr, "E2E WARN: lcmaps_term nonzero\n");

	printf("E2E: policy acquisition_policy: ban_fqan -> voms_localaccount\n");
	printf("E2E: mapped FQAN %s -> uid=%d primary-gid-count=%d\n",
	       TEST_FQAN, (int)out_uid, npg);

	if (out_uid != 0) {
		printf("E2E FAIL: expected the FQAN to be mapped to root (uid 0), got %d\n",
		       (int)out_uid);
		return 1;
	}
	if (npg < 1) {
		printf("E2E FAIL: no primary gid returned\n");
		return 1;
	}
	printf("E2E PASS\n");
	return 0;
}

int main(int argc, char **argv)
{
	const char *pkg_root, *workdir;
	char cwdbuf[1024];
	int rc;

	if (argc < 2) {
		fprintf(stderr, "usage: %s <package_root>\n", argv[0]);
		return 2;
	}
	pkg_root = argv[1];
	workdir = getcwd(cwdbuf, sizeof(cwdbuf)) != NULL ? cwdbuf : ".";

	rc = run_evaluation(pkg_root, workdir);
	if (rc == 3) {
		/* transient failure: retry once after a longer settle delay */
		fprintf(stderr, "E2E INFO: transient failure, retrying once\n");
		sleep(2);
		rc = run_evaluation(pkg_root, workdir);
	}
	return rc;
}
