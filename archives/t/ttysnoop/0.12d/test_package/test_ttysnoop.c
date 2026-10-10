/*
 * Consumer test for the packaged ttysnoop 0.12d tools (HarmonyOS PC / OHOS).
 *
 *   usage: ./test_ttysnoop <path/to/ttysnoops> <path/to/ttysnoop>
 *
 * Run it from the directory that holds this binary: ttysnoops executes it
 * again ("./test_ttysnoop --child") as the snooped login program.
 *
 *   S1  ttysnoops on a pty mirrors a login session to a second pty named in
 *       snooptab: UNIX98 pty for the child, controlling terminal, input from
 *       both ttys reaches the child, output reaches both, clean exit.
 *   S2  ttysnoop client error paths (usage, no server, over-long pty name).
 *   S3  socket mode: server socket in TTYSNOOP_SPOOLDIR, client connects,
 *       a wrong password is rejected.  Needs AF_UNIX bind() in the work
 *       directory; skipped (and reported) where the filesystem refuses it.
 */
#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/un.h>
#include <sys/utsname.h>
#include <sys/wait.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

#define TIMEOUT_MS 15000
#define SPOOL "tsnoop-spool"

struct stream {
	int fd, closed;
	size_t len;
	char buf[16384];
};

static int checks, failures;
static char self_prog[128];

static void check(int ok, const char *what, const char *detail)
{
	checks++;
	failures += !ok;
	printf("%s %d - %s%s%s\n", ok ? "ok" : "not ok", checks, what,
	       detail ? " -- " : "", detail ? detail : "");
	fflush(stdout);
}

static long now_ms(void)
{
	struct timespec ts;

	clock_gettime(CLOCK_MONOTONIC, &ts);
	return ts.tv_sec * 1000L + ts.tv_nsec / 1000000L;
}

/* collect whatever the streams have to offer, waiting up to ms */
static void pump(struct stream *s[], int n, int ms)
{
	struct pollfd p[4];
	int i;

	for (i = 0; i < n; i++) {
		p[i].fd = s[i]->closed ? -1 : s[i]->fd;
		p[i].events = POLLIN;
		p[i].revents = 0;
	}
	if (poll(p, n, ms) <= 0)
		return;
	for (i = 0; i < n; i++) {
		size_t room = sizeof(s[i]->buf) - 1 - s[i]->len;
		ssize_t r;

		if (!(p[i].revents & (POLLIN | POLLHUP | POLLERR)))
			continue;
		r = room ? read(s[i]->fd, s[i]->buf + s[i]->len, room) : 0;
		if (r <= 0) {
			s[i]->closed = 1;
			continue;
		}
		for (; r > 0; r--, s[i]->len++)
			if (s[i]->buf[s[i]->len] == 0)
				s[i]->buf[s[i]->len] = '.';
		s[i]->buf[s[i]->len] = 0;
	}
}

static int wait_for(struct stream *all[], int n, struct stream *s, const char *needle)
{
	long end = now_ms() + TIMEOUT_MS;

	while (!strstr(s->buf, needle)) {
		long left = end - now_ms();

		if (left <= 0 || s->closed)
			return strstr(s->buf, needle) != NULL;
		pump(all, n, left > 200 ? 200 : (int) left);
	}
	return 1;
}

static int wait_exit(pid_t pid, struct stream *all[], int n, int *status)
{
	long end = now_ms() + TIMEOUT_MS;

	for (;;) {
		if (waitpid(pid, status, WNOHANG) == pid)
			return 1;
		if (now_ms() > end) {
			kill(pid, SIGKILL);
			waitpid(pid, status, 0);
			return 0;
		}
		pump(all, n, 100);
	}
}

static const char *describe(int status, char *buf, size_t n)
{
	if (WIFEXITED(status))
		snprintf(buf, n, "exit status %d", WEXITSTATUS(status));
	else if (WIFSIGNALED(status))
		snprintf(buf, n, "killed by signal %d", WTERMSIG(status));
	else
		snprintf(buf, n, "status 0x%x", status);
	return buf;
}

static void dump(const char *tag, const struct stream *s)
{
	printf("# --- %s (%zu bytes) ---\n# %s\n", tag, s->len, s->buf);
}

static int open_pty(char *name, size_t size)
{
	int fd = posix_openpt(O_RDWR | O_NOCTTY);
	char *n;

	if (fd < 0)
		return -1;
	if (grantpt(fd) || unlockpt(fd) || (n = ptsname(fd)) == NULL || strlen(n) >= size) {
		close(fd);
		return -1;
	}
	strcpy(name, n);
	fcntl(fd, F_SETFD, FD_CLOEXEC);
	return fd;
}

static int write_tab(const char *path, const char *snoopdev)
{
	FILE *f = fopen(path, "w");

	if (f == NULL)
		return -1;
	fprintf(f, "# written by test_ttysnoop\n*\t%s\tlogin\t%s\n", snoopdev, self_prog);
	return fclose(f);
}

/* start ttysnoops the way getty/telnetd would: as session leader on a tty */
static pid_t start_server(const char *ttysnoops, const char *slave, const char *tab)
{
	pid_t pid;

	fflush(NULL);
	if ((pid = fork()) == 0) {
		int fd;

		setsid();
		if ((fd = open(slave, O_RDWR)) < 0)
			_exit(126);
		ioctl(fd, TIOCSCTTY, 0);
		dup2(fd, 0);
		dup2(fd, 1);
		dup2(fd, 2);
		if (fd > 2)
			close(fd);
		setenv("TTYSNOOP_SNOOPTAB", tab, 1);
		setenv("TTYSNOOP_SPOOLDIR", SPOOL, 1);
		execl(ttysnoops, "ttysnoops", "--child", (char *) NULL);
		_exit(127);
	}
	return pid;
}

static pid_t start_client(const char *ttysnoop, const char *arg, int *in_w, int *out_r)
{
	int in[2], out[2];
	pid_t pid;

	if (pipe(in) || pipe(out))
		return -1;
	fflush(NULL);
	if ((pid = fork()) == 0) {
		dup2(in[0], 0);
		dup2(out[1], 1);
		dup2(out[1], 2);
		close(in[0]); close(in[1]); close(out[0]); close(out[1]);
		setenv("TTYSNOOP_SPOOLDIR", SPOOL, 1);
		execl(ttysnoop, "ttysnoop", arg, (char *) NULL);
		_exit(127);
	}
	close(in[0]);
	close(out[1]);
	*in_w = in[1];
	*out_r = out[0];
	return pid;
}

/* run the client to completion without input; returns its wait status */
static int client_once(const char *ttysnoop, const char *arg, struct stream *out)
{
	int in_w, status = -1;
	pid_t pid = start_client(ttysnoop, arg, &in_w, &out->fd);
	struct stream *all[1] = { out };

	if (pid < 0)
		return -1;
	if (!wait_exit(pid, all, 1, &status))
		printf("# client did not terminate, killed\n");
	while (!out->closed)
		pump(all, 1, 200);
	close(in_w);
	close(out->fd);
	return status;
}

static int child_main(void)
{
	char line[256];
	const char *tty = ttyname(STDIN_FILENO);
	int ctty = open("/dev/tty", O_RDWR | O_NOCTTY), round = 0;

	printf("CHILD-READY tty=%s ctty=%s\n", tty ? tty : "?", ctty >= 0 ? "yes" : "no");
	fflush(stdout);
	while (fgets(line, sizeof(line), stdin) != NULL) {
		line[strcspn(line, "\r\n")] = 0;
		if (strcmp(line, "quit") == 0)
			break;
		printf("CHILD-ECHO%d:%s\n", ++round, line);
		fflush(stdout);
	}
	return 0;
}

static void scenario_tty(const char *ttysnoops)
{
	struct stream a = { 0 }, b = { 0 };
	struct stream *all[2] = { &a, &b };
	char sa[64], sb[64], tty[64] = "?", info[256];
	const char *p;
	int status = -1;
	pid_t pid;

	if ((a.fd = open_pty(sa, sizeof(sa))) < 0 || (b.fd = open_pty(sb, sizeof(sb))) < 0
	    || write_tab("tsnoop-tty.tab", sb) != 0) {
		check(0, "S1 set up two ptys and the snooptab", strerror(errno));
		return;
	}
	pid = start_server(ttysnoops, sa, "tsnoop-tty.tab");
	printf("# S1 session tty %s, snoop tty %s, ttysnoops pid %d\n", sa, sb, (int) pid);

	check(wait_for(all, 2, &a, "CHILD-READY"), "S1 ttysnoops runs the login program and relays it to the session tty", NULL);
	check(wait_for(all, 2, &b, "CHILD-READY"), "S1 the session is mirrored to the snoop tty from snooptab", NULL);
	if ((p = strstr(a.buf, "CHILD-READY tty=")) != NULL)
		sscanf(p, "CHILD-READY tty=%63s", tty);
	snprintf(info, sizeof(info), "child tty %s", tty);
	check(strcmp(tty, "?") && strcmp(tty, sa) && strcmp(tty, sb),
	      "S1 the login program runs on a pty allocated by ttysnoops (posix_openpt/ptsname)", info);
	check(strstr(a.buf, "ctty=yes") != NULL, "S1 that pty is the login program's controlling terminal", NULL);

	write(a.fd, "hello-from-user\r", 16);
	check(wait_for(all, 2, &a, "CHILD-ECHO1:hello-from-user"), "S1 input typed on the session tty reaches the login program", NULL);
	check(wait_for(all, 2, &b, "CHILD-ECHO1:hello-from-user"), "S1 its answer is mirrored to the snoop tty", NULL);

	write(b.fd, "hello-from-snooper\r", 19);
	check(wait_for(all, 2, &a, "CHILD-ECHO2:hello-from-snooper"), "S1 input typed on the snoop tty is injected into the session", NULL);
	check(wait_for(all, 2, &b, "CHILD-ECHO2:hello-from-snooper"), "S1 the snoop tty sees the answer to its own input", NULL);

	write(a.fd, "quit\r", 5);
	wait_exit(pid, all, 2, &status);
	check(WIFEXITED(status) && WEXITSTATUS(status) == 0,
	      "S1 ttysnoops exits 0 when the login program ends (utmp cleanup included)",
	      describe(status, info, sizeof(info)));
	if (failures) {
		dump("session tty", &a);
		dump("snoop tty", &b);
	}
	close(a.fd);
	close(b.fd);
}

static void scenario_client(const char *ttysnoop)
{
	struct stream out;
	char longname[160], info[64];
	int status;

	memset(&out, 0, sizeof(out));
	status = client_once(ttysnoop, NULL, &out);
	check(WIFEXITED(status) && WEXITSTATUS(status) == 1 && strstr(out.buf, "Usage: ttysnoop <pty>"),
	      "S2 ttysnoop without a pty argument prints its usage and exits 1", describe(status, info, sizeof(info)));

	memset(&out, 0, sizeof(out));
	status = client_once(ttysnoop, "no-such-pty", &out);
	check(WIFEXITED(status) && WEXITSTATUS(status) == 1 && strstr(out.buf, "can't connect to server"),
	      "S2 ttysnoop reports a missing server and exits 1", describe(status, info, sizeof(info)));

	memset(longname, 'x', sizeof(longname) - 1);
	longname[sizeof(longname) - 1] = 0;
	memset(&out, 0, sizeof(out));
	status = client_once(ttysnoop, longname, &out);
	check(WIFEXITED(status) && WEXITSTATUS(status) == 1 && strstr(out.buf, "socket path too long"),
	      "S2 an over-long pty name is refused instead of overflowing the socket path",
	      describe(status, info, sizeof(info)));
}

static int probe_bind(char *why, size_t n)
{
	struct sockaddr_un addr;
	int fd = socket(AF_UNIX, SOCK_STREAM, 0), ok;

	memset(&addr, 0, sizeof(addr));
	addr.sun_family = AF_UNIX;
	snprintf(addr.sun_path, sizeof(addr.sun_path), "%s/.probe", SPOOL);
	unlink(addr.sun_path);
	ok = fd >= 0 && bind(fd, (struct sockaddr *) &addr, sizeof(addr)) == 0;
	if (!ok)
		snprintf(why, n, "errno %d (%s)", errno, strerror(errno));
	if (fd >= 0)
		close(fd);
	unlink(addr.sun_path);
	return ok;
}

static int find_socket(char *name, size_t n)
{
	long end = now_ms() + TIMEOUT_MS;

	while (now_ms() < end) {
		DIR *d = opendir(SPOOL);
		struct dirent *e;
		struct stat st;
		char path[256];

		while (d && (e = readdir(d)) != NULL) {
			snprintf(path, sizeof(path), "%s/%s", SPOOL, e->d_name);
			if (e->d_name[0] != '.' && lstat(path, &st) == 0 && S_ISSOCK(st.st_mode)
			    && strlen(e->d_name) < n) {
				strcpy(name, e->d_name);
				closedir(d);
				return 1;
			}
		}
		if (d)
			closedir(d);
		usleep(100000);
	}
	return 0;
}

static void scenario_socket(const char *ttysnoops, const char *ttysnoop)
{
	struct stream c = { 0 }, cl = { 0 };
	struct stream *all[2] = { &c, &cl };
	char sc[64], sock[64], why[128], info[64];
	int status = -1, in_w = -1, prompt;
	pid_t pid, cpid;

	if (!probe_bind(why, sizeof(why))) {
		printf("skip - S3 socket mode: this filesystem refuses AF_UNIX bind() in %s: %s\n", SPOOL, why);
		return;
	}
	if ((c.fd = open_pty(sc, sizeof(sc))) < 0 || write_tab("tsnoop-sock.tab", "socket") != 0) {
		check(0, "S3 set up a pty and the snooptab", strerror(errno));
		return;
	}
	pid = start_server(ttysnoops, sc, "tsnoop-sock.tab");
	check(wait_for(all, 1, &c, "CHILD-READY") && find_socket(sock, sizeof(sock)),
	      "S3 ttysnoops publishes its session socket in TTYSNOOP_SPOOLDIR", NULL);

	cpid = start_client(ttysnoop, sock, &in_w, &cl.fd);
	prompt = wait_for(all, 2, &cl, "Snoop password:");
	if (prompt)
		write(in_w, "wrong-password\r", 15);
	wait_exit(cpid, all, 2, &status);
	while (!cl.closed)
		pump(all, 2, 200);
	printf("# S3 client %s the password prompt\n", prompt ? "got" : "was refused before");
	check(!strstr(cl.buf, "can't connect") && (prompt || !strstr(cl.buf, "Verified")),
	      "S3 the ttysnoop client connects to the server socket", NULL);
	check(WIFEXITED(status) && WEXITSTATUS(status) == 0 && strstr(cl.buf, "Back at local tty.")
	      && !strstr(cl.buf, "Verified OK") && (!prompt || strstr(cl.buf, "Password incorrect.")),
	      "S3 a wrong password is rejected and the server hangs up", describe(status, info, sizeof(info)));
	close(in_w);
	close(cl.fd);

	write(c.fd, "quit\r", 5);
	wait_exit(pid, all, 1, &status);
	check(WIFEXITED(status) && WEXITSTATUS(status) == 0,
	      "S3 ttysnoops exits 0 when the login program ends", describe(status, info, sizeof(info)));
	if (failures) {
		dump("session tty", &c);
		dump("client", &cl);
	}
	close(c.fd);
}

/* privileged runs must keep the compiled-in paths (conf_path guard) */
static void scenario_privileged(const char *ttysnoops)
{
	struct stream a = { 0 };
	struct stream *all[1] = { &a };
	char sa[64], info[64];
	int status = -1;
	pid_t pid;

	if (access("/etc/snooptab", F_OK) == 0 || (a.fd = open_pty(sa, sizeof(sa))) < 0
	    || write_tab("tsnoop-tty.tab", "socket") != 0) {
		printf("skip - privileged override check (/etc/snooptab exists or no pty)\n");
		return;
	}
	pid = start_server(ttysnoops, sa, "tsnoop-tty.tab");
	wait_exit(pid, all, 1, &status);
	pump(all, 1, 200);
	check(strstr(a.buf, "can't open /etc/snooptab") && WIFEXITED(status) && WEXITSTATUS(status) == 1,
	      "privileged ttysnoops ignores TTYSNOOP_SNOOPTAB", describe(status, info, sizeof(info)));
	close(a.fd);
}

int main(int argc, char *argv[])
{
	struct utsname u;
	const char *base;

	if (argc == 2 && strcmp(argv[1], "--child") == 0)
		return child_main();
	if (argc != 3) {
		fprintf(stderr, "usage: %s <ttysnoops> <ttysnoop>\n", argv[0]);
		return 2;
	}
	signal(SIGPIPE, SIG_IGN);
	alarm(300);
	base = strrchr(argv[0], '/') ? strrchr(argv[0], '/') + 1 : argv[0];
	snprintf(self_prog, sizeof(self_prog), "./%s", base);
	if (access(self_prog, X_OK) != 0) {
		fprintf(stderr, "run from the directory holding %s\n", base);
		return 2;
	}
	uname(&u);
	printf("# %s %s %s, euid %d\n", u.sysname, u.release, u.machine, (int) geteuid());
	mkdir(SPOOL, 0700);

	if (geteuid() == 0) {
		printf("skip - S1/S3 need an unprivileged user: TTYSNOOP_* overrides are ignored for root\n");
		scenario_privileged(argv[1]);
	} else {
		scenario_tty(argv[1]);
	}
	scenario_client(argv[2]);
	if (geteuid() != 0)
		scenario_socket(argv[1], argv[2]);

	printf("# ttysnoop consumer test: %d checks, %d failed\n", checks, failures);
	return failures ? 1 : 0;
}
