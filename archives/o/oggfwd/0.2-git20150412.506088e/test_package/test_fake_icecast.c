/*
 * Consumer test for the oggfwd package: a fake Icecast server that oggfwd
 * (linked against libshout) connects to. Checks the real HTTP source
 * handshake, metadata-file / CLI option handling and the error paths.
 */
#define _GNU_SOURCE
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/wait.h>
#include <unistd.h>

static int failures;

#define CHECK(cond, msg)                                                   \
	do {                                                               \
		if (cond) {                                                \
			printf("PASS: %s\n", msg);                         \
		} else {                                                   \
			printf("FAIL: %s\n", msg);                         \
			failures++;                                        \
		}                                                          \
	} while (0)

/* Run oggfwd with stdin from /dev/null; stdout+stderr are captured into out. */
static pid_t spawn(const char *exe, char *const argv[], int *out_fd)
{
	int p[2];
	pid_t pid;

	if (pipe(p) != 0)
		return -1;
	pid = fork();
	if (pid == 0) {
		int nul = open("/dev/null", O_RDONLY);
		dup2(nul, 0);
		dup2(p[1], 1);
		dup2(p[1], 2);
		close(p[0]);
		close(p[1]);
		execv(exe, argv);
		_exit(127);
	}
	close(p[1]);
	*out_fd = p[0];
	return pid;
}

static int reap(pid_t pid, int fd, char *out, size_t outsz)
{
	int st = 0;
	ssize_t n, len = 0;

	waitpid(pid, &st, 0);
	while ((n = read(fd, out + len, outsz - 1 - len)) > 0)
		len += n;
	out[len] = 0;
	close(fd);
	return WIFEXITED(st) ? WEXITSTATUS(st) : -1;
}

int main(int argc, char **argv)
{
	char out[4096], req[8192], portstr[16];
	char metafile[512];
	const char *tmpdir = getenv("TMPDIR");
	const char *deny = "HTTP/1.0 401 Unauthorized\r\nWWW-Authenticate: Basic realm=\"Icecast\"\r\n"
			   "Content-Length: 0\r\nConnection: close\r\n\r\n";
	int attempt, saw_unauth_probe = 0;
	const char *resp = "HTTP/1.0 200 OK\r\nContent-Type: text/plain\r\n\r\n";
	const char *meta = "# comment\nname=NameFromMeta\ndescription=DescFromMetaFile\n";
	struct sockaddr_in sa;
	socklen_t sl = sizeof(sa);
	int srv, conn, fd, rc, mfd;
	ssize_t n, len;
	pid_t pid;
	int has_tls = 0;

	if (argc != 2) {
		fprintf(stderr, "usage: %s /path/to/oggfwd\n", argv[0]);
		return 2;
	}
	setvbuf(stdout, NULL, _IOLBF, 0);
	signal(SIGPIPE, SIG_IGN);
	alarm(60);

	/* 1. usage banner / exit status */
	{
		char *a[] = {argv[1], "-h", NULL};
		pid = spawn(argv[1], a, &fd);
		rc = reap(pid, fd, out, sizeof(out));
		CHECK(rc == 1 && strstr(out, "usage: ") && strstr(out, "address port password mountpoint"),
		      "oggfwd -h prints usage and exits 1");
		/* libshout built with TLS: oggfwd offers -T; disable the OPTIONS/TLS probe so the plain fake server works */
		has_tls = strstr(out, "[-T ") != NULL;
	}

	/* 2. wrong number of arguments */
	{
		char *a[] = {argv[1], "127.0.0.1", "8000", NULL};
		pid = spawn(argv[1], a, &fd);
		rc = reap(pid, fd, out, sizeof(out));
		CHECK(rc == 1 && strstr(out, "Wrong number of arguments"), "missing arguments are rejected");
	}

	/* 3. real handshake against a fake Icecast server */
	srv = socket(AF_INET, SOCK_STREAM, 0);
	memset(&sa, 0, sizeof(sa));
	sa.sin_family = AF_INET;
	sa.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
	sa.sin_port = 0;
	if (srv < 0 || bind(srv, (struct sockaddr *)&sa, sizeof(sa)) != 0 || listen(srv, 4) != 0 ||
	    getsockname(srv, (struct sockaddr *)&sa, &sl) != 0) {
		perror("fake server setup");
		return 2;
	}
	snprintf(portstr, sizeof(portstr), "%d", ntohs(sa.sin_port));

	snprintf(metafile, sizeof(metafile), "%s/oggfwd-meta-XXXXXX", tmpdir && *tmpdir ? tmpdir : ".");
	mfd = mkstemp(metafile);
	if (mfd < 0 || write(mfd, meta, strlen(meta)) != (ssize_t)strlen(meta)) {
		perror("metafile");
		return 2;
	}
	close(mfd);

	{
		char *a[] = {argv[1], "-m", metafile, "-n", "NameFromCli", "-g", "TestGenre", "-p",
			     "-T", "disabled", "127.0.0.1", portstr, "hackme", "/test.ogg", NULL};
		if (!has_tls) { /* drop "-T disabled" */
			memmove(&a[8], &a[10], 5 * sizeof(char *));
		}
		pid = spawn(argv[1], a, &fd);
	}
	/*
	 * Behave like Icecast: a source request without credentials is answered
	 * with 401 + WWW-Authenticate, the authenticated retry gets 200 OK.
	 */
	for (attempt = 0; attempt < 3; attempt++) {
		conn = accept(srv, NULL, NULL);
		if (conn < 0)
			break;
		len = 0;
		while (len < (ssize_t)sizeof(req) - 1) {
			n = read(conn, req + len, sizeof(req) - 1 - len);
			if (n <= 0)
				break;
			len += n;
			req[len] = 0;
			if (strstr(req, "\r\n\r\n"))
				break;
		}
		req[len > 0 ? len : 0] = 0;
		if (strstr(req, "Authorization: Basic")) {
			(void)!write(conn, resp, strlen(resp));
			break;
		}
		saw_unauth_probe = 1;
		(void)!write(conn, deny, strlen(deny));
		close(conn);
		conn = -1;
	}
	CHECK(conn >= 0, "oggfwd connected to the fake Icecast server");
	CHECK(saw_unauth_probe, "libshout retries with credentials after a 401 challenge");
	rc = reap(pid, fd, out, sizeof(out));
	if (conn >= 0)
		close(conn);
	unlink(metafile);

	CHECK(strstr(req, "/test.ogg") != NULL, "request targets the requested mountpoint");
	CHECK(strstr(req, "Authorization: Basic c291cmNlOmhhY2ttZQ==") != NULL,
	      "source credentials are sent as HTTP Basic auth");
	CHECK(strstr(req, "NameFromCli") != NULL && strstr(req, "NameFromMeta") == NULL,
	      "-n overrides the name from the -m metadata file");
	CHECK(strstr(req, "DescFromMetaFile") != NULL, "-m metadata file description reaches the server");
	CHECK(strstr(req, "TestGenre") != NULL, "-g genre reaches the server");
	CHECK(rc == 0 && strstr(out, "Connected to server") && strstr(out, "Total bytes read: 0"),
	      "empty stdin: connects, reports 0 bytes and exits 0");
	close(srv);

	/* 4. connection to a closed port fails cleanly */
	{
		char *a[] = {argv[1], "-T", "disabled", "127.0.0.1", portstr, "hackme", "/test.ogg", NULL};
		if (!has_tls)
			memmove(&a[1], &a[3], 5 * sizeof(char *));
		pid = spawn(argv[1], a, &fd);
		rc = reap(pid, fd, out, sizeof(out));
		CHECK(rc == 1 && strstr(out, "Error connecting"), "connection refused is reported, exit 1");
	}

	printf("%s (%d failure(s))\n", failures ? "FAILED" : "ALL PASSED", failures);
	return failures ? 1 : 0;
}
