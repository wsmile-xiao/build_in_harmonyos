/* test_package/pwshim.c - HarmonyOS functional-test fixture (LD_PRELOAD only).
 *
 * The OHOS device user runs as a uid (e.g. 20020100) that has NO entry in
 * /etc/passwd, and the volume is not writable / has no useradd. gnubatch's
 * password tools assume the invoking account resolves through the libc
 * password database:
 *   - gbch-passwd (no -u) calls getpwuid(getuid()) to learn the account
 *     name, else it prints "Unable to find current uid <n> in pw file"
 *     and exits 4;
 *   - with -u <other> it requires root (getuid()==0) and exits 3.
 * So the password-subsystem round trip (test_package/test.sh cases 4-7)
 * cannot run on-device, even though it would on a root CI.
 *
 * This fixture is compiled at test time and LD_PRELOADed ONLY for the test
 * binaries. It supplies a synthetic passwd entry for exactly the invoking
 * uid (name "gnubatch"), delegating every other lookup to the real libc.
 * No product code is modified: gbch-passwd still writes a real gbpwfile via
 * crypt(), and btpwchk still authenticates against it with crypt().
 */
#define _GNU_SOURCE
#include <pwd.h>
#include <string.h>
#include <unistd.h>
#include <dlfcn.h>

#define GB_TEST_USER "gnubatch"

static struct passwd g_pw;

static struct passwd *gb_fill(void)
{
	g_pw.pw_name   = (char *) GB_TEST_USER;
	g_pw.pw_passwd = (char *) "x";
	g_pw.pw_uid    = getuid();
	g_pw.pw_gid    = getgid();
	g_pw.pw_gecos  = (char *) "gnubatch test fixture";
	g_pw.pw_dir    = (char *) "/tmp";
	g_pw.pw_shell  = (char *) "/bin/sh";
	return &g_pw;
}

struct passwd *getpwuid(uid_t uid)
{
	struct passwd *(*real)(uid_t);
	if (uid == getuid())
		return gb_fill();
	real = (struct passwd *(*)(uid_t)) dlsym(RTLD_NEXT, "getpwuid");
	return real ? real(uid) : (struct passwd *) 0;
}

struct passwd *getpwnam(const char *name)
{
	struct passwd *(*real)(const char *);
	if (name && strcmp(name, GB_TEST_USER) == 0)
		return gb_fill();
	real = (struct passwd *(*)(const char *)) dlsym(RTLD_NEXT, "getpwnam");
	return real ? real(name) : (struct passwd *) 0;
}
