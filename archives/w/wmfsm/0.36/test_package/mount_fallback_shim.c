#define _GNU_SOURCE

#include <dlfcn.h>
#include <errno.h>
#include <stdio.h>
#include <string.h>
#include <sys/vfs.h>
#include <unistd.h>

typedef struct _XDisplay Display;
typedef FILE *(*fopen_fn)(const char *, const char *);
typedef int (*statfs_fn)(const char *, struct statfs *);

static int mtab_open_rejected;
static int proc_mounts_opened;
static int mount_scan_started;

FILE *fopen(const char *path, const char *mode)
{
	static fopen_fn real_fopen;
	FILE *result;

	if (strcmp(path, "/etc/mtab") == 0) {
		mtab_open_rejected = 1;
		errno = ENOENT;
		return NULL;
	}
	if (!real_fopen)
		real_fopen = (fopen_fn)dlsym(RTLD_NEXT, "fopen");
	if (!real_fopen) {
		errno = ENOSYS;
		return NULL;
	}
	result = real_fopen(path, mode);
	if (result && strcmp(path, "/proc/mounts") == 0)
		proc_mounts_opened = 1;
	return result;
}

int statfs(const char *path, struct statfs *buffer)
{
	static statfs_fn real_statfs;
	int result;

	if (!real_statfs)
		real_statfs = (statfs_fn)dlsym(RTLD_NEXT, "statfs");
	if (!real_statfs) {
		errno = ENOSYS;
		return -1;
	}
	result = real_statfs(path, buffer);
	if (mount_scan_started && proc_mounts_opened && result == 0 &&
	    path && path[0] == '/') {
		static const char success[] = "WMFSM_PROC_MOUNTS_STATFS_OK\n";
		(void)write(STDERR_FILENO, success, sizeof(success) - 1);
		_exit(86);
	}
	return result;
}

/* Keep the real application flow headless; filesystem work remains real. */
void openXwindow(int argc, char *argv[], char **pixmap, char *mask,
		 int width, int height)
{
	(void)argc;
	(void)argv;
	(void)pixmap;
	(void)mask;
	(void)width;
	(void)height;
}

/*
 * readFileSystems() runs before the event loop. Let its first event poll return
 * normally so the app executes statfs() for its parsed mount entries. The
 * statfs interposer terminates immediately after the first successful call,
 * before the headless app reaches any X11 drawing operation.
 */
int XPending(Display *display)
{
	static const char failure[] = "WMFSM_PROC_MOUNTS_STATFS_FAILED\n";
	static unsigned int polls;
	(void)display;

	if (!mtab_open_rejected || !proc_mounts_opened) {
		(void)write(STDERR_FILENO, failure, sizeof(failure) - 1);
		_exit(87);
	}
	if (polls++ == 0) {
		mount_scan_started = 1;
		return 0;
	}

	(void)write(STDERR_FILENO, failure, sizeof(failure) - 1);
	_exit(87);
}
