/*
 * mmhshim — OHOS launcher shim for mmh's shell-script commands.
 *
 * The OHOS kernel refuses execve() of shebang scripts (rc 126 EACCES),
 * regardless of mode bits, so the installed bin/<cmd> scripts (mmh, mhsign,
 * mhpgp, print-mimetype, sendfiles, whatnow2) cannot be run directly.
 * The suite installs this launcher under the command name and renames the
 * real script to <cmd>.real.  The launcher resolves its own directory via
 * /proc/self/exe and executes <dir>/<cmd>.real through a POSIX shell,
 * passing all arguments through.
 *
 * Build (device):  clang -O2 -o mmhshim mmhshim.c
 */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <unistd.h>

static const char *shells[] = {
	"/bin/sh",
	"/data/service/hnp/bin/bash",
	"/system/bin/sh",
	NULL
};

int
main(int argc, char **argv)
{
	char exe[4096], script[4400], *slash, *base;
	char **nargv;
	size_t blen;
	ssize_t n;
	int i;

	n = readlink("/proc/self/exe", exe, sizeof(exe) - 1);
	if (n > 0) {
		exe[n] = '\0';
		slash = strrchr(exe, '/');
		if (slash == NULL) {
			fprintf(stderr, "mmhshim: cannot resolve own directory\n");
			return 126;
		}
		*slash = '\0';
	} else {
		/* fallback: argv[0] must contain a slash */
		slash = strrchr(argv[0], '/');
		if (slash == NULL) {
			fprintf(stderr, "mmhshim: cannot resolve own path from argv[0]\n");
			return 126;
		}
		memcpy(exe, argv[0], (size_t)(slash - argv[0]));
		exe[slash - argv[0]] = '\0';
	}

	base = strrchr(argv[0], '/');
	base = (base != NULL) ? base + 1 : argv[0];
	blen = strlen(base);
	if (blen > 5 && strcmp(base + blen - 5, ".real") == 0)
		snprintf(script, sizeof(script), "%s/%s", exe, base);
	else
		snprintf(script, sizeof(script), "%s/%s.real", exe, base);

	if (access(script, R_OK) != 0) {
		fprintf(stderr, "%s: missing script %s\n", argv[0], script);
		return 126;
	}

	nargv = malloc(sizeof(char *) * (size_t)(argc + 2));
	if (nargv == NULL) {
		fprintf(stderr, "mmhshim: out of memory\n");
		return 126;
	}
	nargv[0] = (char *)"sh";
	nargv[1] = script;
	for (i = 1; i < argc; i++)
		nargv[i + 1] = argv[i];
	nargv[argc + 1] = NULL;

	for (i = 0; shells[i] != NULL; i++)
		execv(shells[i], nargv);

	fprintf(stderr, "mmhshim: no usable shell found\n");
	return 127;
}
