/*
 * Consumer test for the packaged yadifa client.
 *
 * Case 1: the loopback DNS server implemented below answers one A query; the
 *         packaged `yadifa yadig` client must encode the question, send it,
 *         parse the answer and print it.  Both ends assert: the server checks
 *         the encoded qname and qtype, the caller checks the printed answer
 *         and the client exit status.
 * Case 2: `yadifa -V` must report the packaged 3.x version.
 */
#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <netinet/in.h>
#include <poll.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/wait.h>
#include <unistd.h>

#define QNAME_WIRE "\x07""example\x03""org\x00"
#define QNAME_WIRE_LEN 13
#define ANSWER_IP_BYTES "\xc0\x00\x02\x2a"      /* 192.0.2.42 */
#define ANSWER_IP_TEXT "192.0.2.42"
#define VERSION_MARK "3.0"
#define CAPTURE_FILE "yadifa_consumer_capture.txt"

static void die(const char *what)
{
	fprintf(stderr, "FATAL: %s (%s)\n", what, strerror(errno));
	exit(1);
}

static size_t slurp(const char *path, char *buf, size_t cap)
{
	FILE *fp = fopen(path, "rb");
	size_t n = 0;

	if (fp == NULL) {
		buf[0] = '\0';
		return 0;
	}
	n = fread(buf, 1, cap - 1, fp);
	buf[n] = '\0';
	fclose(fp);
	return n;
}

/* Byte length of the question (labels + qtype + qclass), or -1. */
static int question_len(const unsigned char *msg, size_t len)
{
	size_t o = 12;

	while (o < len && msg[o] != 0) {
		if ((msg[o] & 0xc0) != 0) {
			return -1;
		}
		o += msg[o] + 1;
	}
	if (o + 5 > len) {
		return -1;
	}
	return (int) (o + 1 - 12 + 4);
}

static int serve_one_query(int fd)
{
	unsigned char query[1024];
	unsigned char answer[512];
	unsigned char ip[4] = { 192, 0, 2, 42 };
	struct sockaddr_storage from;
	socklen_t from_len = sizeof from;
	struct pollfd pfd;
	ssize_t got;
	size_t o;
	int qlen;

	pfd.fd = fd;
	pfd.events = POLLIN;
	if (poll(&pfd, 1, 10000) <= 0) {
		fprintf(stderr, "server: no query arrived\n");
		return 1;
	}
	got = recvfrom(fd, query, sizeof query, 0, (struct sockaddr *) &from, &from_len);
	if (got < (ssize_t) (12 + QNAME_WIRE_LEN + 4)) {
		fprintf(stderr, "server: short query (%zd bytes)\n", got);
		return 1;
	}
	if (memcmp(&query[12], QNAME_WIRE, QNAME_WIRE_LEN) != 0) {
		fprintf(stderr, "server: encoded qname is not example.org\n");
		return 1;
	}
	if (query[12 + QNAME_WIRE_LEN] != 0 || query[12 + QNAME_WIRE_LEN + 1] != 1) {
		fprintf(stderr, "server: qtype is not A\n");
		return 1;
	}
	qlen = question_len(query, (size_t) got);
	if (qlen < 0) {
		fprintf(stderr, "server: malformed question section\n");
		return 1;
	}

	memset(answer, 0, sizeof answer);
	answer[0] = query[0];
	answer[1] = query[1];
	answer[2] = (unsigned char) (0x84 | (query[2] & 0x01));   /* QR + AA + RD */
	answer[3] = 0x80;                                         /* RA, rcode NOERROR */
	answer[5] = 1;                                            /* QDCOUNT */
	answer[7] = 1;                                            /* ANCOUNT */
	o = 12;
	memcpy(&answer[o], &query[12], (size_t) qlen);
	o += (size_t) qlen;
	answer[o++] = 0xc0;
	answer[o++] = 0x0c;                    /* NAME pointer to the question */
	answer[o++] = 0x00;
	answer[o++] = 0x01;                    /* TYPE A */
	answer[o++] = 0x00;
	answer[o++] = 0x01;                    /* CLASS IN */
	answer[o++] = 0x00;
	answer[o++] = 0x00;
	answer[o++] = 0x00;
	answer[o++] = 0x3c;                    /* TTL 60 */
	answer[o++] = 0x00;
	answer[o++] = 0x04;                    /* RDLENGTH */
	memcpy(&answer[o], ip, sizeof ip);
	o += sizeof ip;

	if (sendto(fd, answer, o, 0, (struct sockaddr *) &from, from_len) < 0) {
		fprintf(stderr, "server: sendto failed\n");
		return 1;
	}
	fprintf(stderr, "server: answered one query\n");
	return 0;
}

static int run_capture(const char *const argv[], const char *outfile)
{
	pid_t pid;
	int status;
	int fd;

	fd = open(outfile, O_WRONLY | O_CREAT | O_TRUNC, 0600);
	if (fd < 0) {
		die("open capture file");
	}
	pid = fork();
	if (pid < 0) {
		die("fork");
	}
	if (pid == 0) {
		dup2(fd, STDOUT_FILENO);
		dup2(fd, STDERR_FILENO);
		close(fd);
		execv(argv[0], (char *const *) argv);
		_exit(127);
	}
	close(fd);
	if (waitpid(pid, &status, 0) < 0) {
		die("waitpid");
	}
	return WIFEXITED(status) ? WEXITSTATUS(status) : -1;
}

int main(int argc, char *argv[])
{
	char capture[4096];
	char client[PATH_MAX];
	char port_text[8];
	const char *bin_dir;
	const char *query_argv[11];
	const char *version_argv[3];
	struct sockaddr_in addr;
	socklen_t addr_len = sizeof addr;
	pid_t srv;
	size_t n;
	int fd, rc, srv_status, status, exit_code = 0;

	if (argc < 2) {
		fprintf(stderr, "usage: %s <package bin dir>\n", argv[0]);
		return 2;
	}
	bin_dir = argv[1];
	snprintf(client, sizeof client, "%s/yadifa", bin_dir);
	if (access(client, X_OK) != 0) {
		fprintf(stderr, "packaged client %s is not executable\n", client);
		return 1;
	}

	fd = socket(AF_INET, SOCK_DGRAM, 0);
	if (fd < 0) {
		die("socket");
	}
	memset(&addr, 0, sizeof addr);
	addr.sin_family = AF_INET;
	addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
	if (bind(fd, (struct sockaddr *) &addr, sizeof addr) != 0) {
		die("bind");
	}
	if (getsockname(fd, (struct sockaddr *) &addr, &addr_len) != 0) {
		die("getsockname");
	}
	snprintf(port_text, sizeof port_text, "%d", ntohs(addr.sin_port));

	srv = fork();
	if (srv < 0) {
		die("fork server");
	}
	if (srv == 0) {
		_exit(serve_one_query(fd));
	}

	query_argv[0] = client;
	// The packaged client is a multi-call binary: the lookup subcommand is
	// dig (yadifa help dig lists ctrl, keygen, zonesign and dig only). Type is
	// pinned to a single A query because the dig default is a and aaaa, which
	// would send two queries at a server that answers exactly one.
	query_argv[1] = "dig";
	query_argv[2] = "-s";
	query_argv[3] = "127.0.0.1";
	query_argv[4] = "-p";
	query_argv[5] = port_text;
	query_argv[6] = "-t";
	query_argv[7] = "a";
	// dig takes the FQDN through -q/--qname: a trailing positional name is
	// ignored and the query goes out for the root label (measured 28-byte
	// packet with an empty qname), which the server below rejects.
	query_argv[8] = "-q";
	query_argv[9] = "example.org";
	query_argv[10] = NULL;
	rc = run_capture(query_argv, CAPTURE_FILE);
	n = slurp(CAPTURE_FILE, capture, sizeof capture);
	if (rc != 0 || n == 0) {
		fprintf(stderr, "FAIL: yadig run (rc=%d, %lu bytes captured):\n%s\n",
			rc, (unsigned long) n, capture);
		exit_code = 1;
	} else if (strstr(capture, ANSWER_IP_TEXT) == NULL) {
		fprintf(stderr, "FAIL: yadig did not print the served A record:\n%s\n", capture);
		exit_code = 1;
	} else {
		printf("PASS: packaged yadig queried 127.0.0.1:%s and printed %s\n",
			port_text, ANSWER_IP_TEXT);
	}

	if (waitpid(srv, &status, 0) < 0) {
		die("waitpid server");
	}
	srv_status = WIFEXITED(status) ? WEXITSTATUS(status) : -1;
	if (srv_status != 0) {
		fprintf(stderr, "FAIL: loopback server rejected the client query (status %d)\n",
			srv_status);
		exit_code = 1;
	} else {
		printf("PASS: server verified the encoded qname and qtype of the request\n");
	}

	version_argv[0] = client;
	version_argv[1] = "-V";
	version_argv[2] = NULL;
	rc = run_capture(version_argv, CAPTURE_FILE);
	n = slurp(CAPTURE_FILE, capture, sizeof capture);
	// Measured on OHOS aarch64: yadifa -V and yadifa --version both print the
	// packaged version but exit with status 1, while yadifa -h exits 0 (the same
	// reading came from the build-tree twin and from the packaged binary, see
	// notes.md). The substantive check here is the version string, so the exit
	// status of -V is not asserted; the exit-0 path is asserted separately.
	if (n == 0 || strstr(capture, VERSION_MARK) == NULL) {
		fprintf(stderr, "FAIL: `yadifa -V` (rc=%d): %s\n", rc, capture);
		exit_code = 1;
	} else {
		printf("PASS: packaged yadifa reports its version: %s", capture);
	}

	close(fd);
	// Success path: a plain option of the packaged binary must exit 0 too.
	version_argv[1] = "-h";
	rc = run_capture(version_argv, CAPTURE_FILE);
	n = slurp(CAPTURE_FILE, capture, sizeof capture);
	if (rc != 0 || n == 0) {
		fprintf(stderr, "FAIL: packaged yadifa -h (rc=%d, bytes=%zu)",
			rc, n);
		exit_code = 1;
	} else {
		printf("PASS: packaged yadifa -h exits 0 (%zu bytes)", n);
	}
	if (exit_code == 0) {
		printf("CONSUMER TEST PASSED (4 assertions)\n");
	}
	return exit_code;
}
