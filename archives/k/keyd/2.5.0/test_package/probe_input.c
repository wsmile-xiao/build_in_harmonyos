/*
 * keyd 2.5.0 consumer probe: exercise the exact kernel interfaces keyd's own
 * startup path touches, from an unprivileged uid, and report the verbatim
 * errno for each one.
 *
 *   src/vkbd/uinput.c:41        open("/dev/uinput", O_WRONLY | O_NONBLOCK)
 *   src/device.c:218            opendir("/dev/input/")
 *   src/device.c:130            open("/dev/input/event*", O_RDWR | O_NONBLOCK)
 *   src/device.c:58             ioctl(fd, EVIOCGBIT(EV_KEY, ...), ...)
 *   src/device.c:260            inotify_init1(IN_NONBLOCK)
 *   src/device.c:266            inotify_add_watch(fd, "/dev/input/", IN_CREATE)
 *
 * A denial is expected on this platform: the reported errno is the evidence, so
 * it is printed verbatim instead of being reduced to a boolean.  Two controls
 * run first (open /dev/null, readdir /dev) -- if either of those failed, the
 * denials below would say nothing about the input subsystem.
 *
 * Exit code: 0 when no case is FAIL, 1 otherwise.  Every input-plane denial is
 * asserted to carry errno=EACCES (see denied() below): a node that is merely
 * absent (ENOENT) is a different mechanism with a different remedy, and
 * scoring it as a pass would erase the distinction this probe exists to
 * record.  Where the kernel actually grants an interface the case reports
 * SKIP (usable) rather than a false failure.
 */

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <stdio.h>
#include <string.h>
#include <sys/inotify.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <unistd.h>

#include <linux/input.h>
#include <linux/uinput.h>

static int npass;
static int nskip;
static int nfail;

static void report(const char *name, long rc, int err, const char *verdict,
		   const char *detail)
{
	printf("CASE %-28s rc=%-4ld errno=%-3d %-24s %s\n", name, rc, err,
	       err ? strerror(err) : "-", verdict);
	if (detail)
		printf("       %-26s %s\n", "", detail);
	if (!strcmp(verdict, "PASS"))
		npass++;
	else if (!strcmp(verdict, "SKIP"))
		nskip++;
	else
		nfail++;
}

/* The mechanism under test is a MAC denial, which this kernel reports as
 * EACCES.  ENOENT (node absent), ENODEV and EPERM (DAC / capability refusal)
 * are separate mechanisms with separate remedies, so they must not score as
 * PASS here -- a pass would no longer distinguish them from EACCES. */
static int denied(int err)
{
	return err == EACCES;
}

static const char *unexpected(int err)
{
	static char buf[80];

	snprintf(buf, sizeof buf, "expected EACCES(13), got %d (%s)", err,
		 strerror(err));
	return buf;
}

static void probe_stat(const char *path, const char *note)
{
	struct stat st;
	char name[80];

	snprintf(name, sizeof name, "stat %s", path);
	if (stat(path, &st) < 0) {
		if (denied(errno))
			report(name, -1, errno, "PASS",
			       "existence undecidable from user space");
		else
			report(name, -1, errno, "FAIL", unexpected(errno));
		return;
	}
	{
		char buf[96];

		snprintf(buf, sizeof buf, "mode=0%o (%s)",
			 (unsigned)(st.st_mode & 07777), note);
		report(name, 0, 0, "SKIP", buf);
	}
}

/* keyd's virtual keyboard: vkbd_init() opens the control node writable and
 * then issues UI_SET_EVBIT/UI_DEV_CREATE. */
static void probe_uinput(void)
{
	int fd = open("/dev/uinput", O_WRONLY | O_NONBLOCK);
	int err = fd < 0 ? errno : 0;

	if (fd < 0) {
		if (denied(err))
			report("open /dev/uinput (w)", -1, err, "PASS",
			       "no fd: UI_SET_EVBIT/UI_DEV_CREATE unreachable");
		else
			report("open /dev/uinput (w)", -1, err, "FAIL",
			       unexpected(err));
		return;
	}
	report("open /dev/uinput (w)", (long)fd, 0, "SKIP", "node writable");
	if (ioctl(fd, UI_SET_EVBIT, EV_KEY) < 0)
		report("ioctl UI_SET_EVBIT", -1, errno, "PASS", "node open, ioctl denied");
	else
		report("ioctl UI_SET_EVBIT", 0, 0, "SKIP", "node usable");
	if (ioctl(fd, UI_DEV_CREATE) < 0)
		report("ioctl UI_DEV_CREATE", -1, errno, "PASS", "node open, create denied");
	else
		report("ioctl UI_DEV_CREATE", 0, 0, "SKIP", "node usable");
	close(fd);
}

/* keyd's read side: every physical keyboard is grabbed as an evdev node. */
static void probe_event(void)
{
	int fd = open("/dev/input/event0", O_RDWR | O_NONBLOCK);
	int err = fd < 0 ? errno : 0;

	if (fd < 0) {
		if (denied(err))
			report("open /dev/input/event0", -1, err, "PASS",
			       "no fd: EVIOCGBIT capability probe unreachable");
		else
			report("open /dev/input/event0", -1, err, "FAIL",
			       unexpected(err));
		return;
	}
	{
		unsigned char bits[64];
		int rc = ioctl(fd, EVIOCGBIT(EV_KEY, sizeof bits), bits);

		report("ioctl EVIOCGBIT(EV_KEY)", (long)rc, rc < 0 ? errno : 0,
		       rc < 0 ? "PASS" : "SKIP", "capability mask probe");
	}
	close(fd);
	report("open /dev/input/event0", (long)fd, 0, "SKIP", "node usable");
}

static void probe_opendir(void)
{
	DIR *d = opendir("/dev/input");
	int err = d ? 0 : errno;

	if (!d) {
		if (denied(err))
			report("opendir /dev/input", -1, err, "PASS",
			       "device discovery sees no keyboards");
		else
			report("opendir /dev/input", -1, err, "FAIL",
			       unexpected(err));
		return;
	}
	{
		char buf[64];
		int n = 0;

		while (readdir(d))
			n++;
		snprintf(buf, sizeof buf, "%d entries visible", n);
		report("opendir /dev/input", 0, 0, "SKIP", buf);
	}
	closedir(d);
}

static void probe_inotify(void)
{
	int fd = inotify_init1(IN_NONBLOCK);

	if (fd < 0) {
		if (denied(errno))
			report("inotify_init1", -1, errno, "PASS",
			       "inotify itself denied");
		else
			report("inotify_init1", -1, errno, "FAIL",
			       unexpected(errno));
		return;
	}
	report("inotify_init1", (long)fd, 0, "PASS", "descriptor created");
	{
		int wd = inotify_add_watch(fd, "/dev/input/", IN_CREATE);

		if (wd < 0)
			report("inotify_add_watch /dev/input", -1, errno,
			       denied(errno) ? "PASS" : "FAIL",
			       "hotplug watch on the keyboard directory");
		else
			report("inotify_add_watch /dev/input", (long)wd, 0, "SKIP",
			       "hotplug watch installed");
	}
	close(fd);
}

int main(void)
{
	int ctrl = open("/dev/null", O_RDONLY);
	DIR *dev;
	int ndev = 0;

	printf("== keyd input-subsystem probe, uid=%d euid=%d ==\n", (int)getuid(),
	       (int)geteuid());

	if (ctrl < 0)
		report("control open /dev/null", -1, errno, "FAIL",
		       "no baseline: denials below prove nothing");
	else {
		char buf[32];

		snprintf(buf, sizeof buf, "fd=%d", ctrl);
		report("control open /dev/null", (long)ctrl, 0, "PASS", buf);
		close(ctrl);
	}

	dev = opendir("/dev");
	if (!dev)
		report("control opendir /dev", -1, errno, "FAIL",
		       "no baseline: denials below prove nothing");
	else {
		char buf[32];

		while (readdir(dev))
			ndev++;
		snprintf(buf, sizeof buf, "%d entries listed", ndev);
		report("control opendir /dev", 0, 0, "PASS", buf);
		closedir(dev);
	}

	probe_stat("/dev/uinput", "uinput control node");
	probe_stat("/sys/class/input", "input class directory");
	probe_stat("/sys/class/misc/uinput/dev", "uinput class record");
	probe_uinput();
	probe_event();
	probe_opendir();
	probe_inotify();

	printf("SUMMARY pass=%d skip=%d fail=%d\n", npass, nskip, nfail);
	printf("VERDICT %s\n", nfail == 0 ? "OK" : "BROKEN");
	return nfail == 0 ? 0 : 1;
}
