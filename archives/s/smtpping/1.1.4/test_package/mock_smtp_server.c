/*
 * mock_smtp_server.c — minimal SMTP responder for the smtpping consumer test.
 *
 * Speaks just enough SMTP for one smtpping probe (-c 1):
 *   220 banner -> 250 for HELO/EHLO, MAIL FROM, RCPT TO -> 354 for DATA ->
 *   250 after the terminating "." -> 221 for QUIT.
 * Every received command line is appended to the transcript file so test.sh
 * can assert the full transaction reached the server.
 *
 * Usage: mock_smtp_server <port> <transcript-file>
 * Exit codes: 0 = complete session (QUIT seen), 2 = setup error,
 *             3 = no connection within 30s / accept failure,
 *             4 = client disconnected before QUIT.
 */
#define _POSIX_C_SOURCE 200809L

#include <arpa/inet.h>
#include <netinet/in.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <strings.h>
#include <sys/socket.h>
#include <unistd.h>

static volatile sig_atomic_t timed_out = 0;

static void on_alarm(int sig)
{
	(void)sig;
	timed_out = 1;
}

static int send_all(int fd, const char *buf)
{
	size_t len = strlen(buf), off = 0;
	while (off < len) {
		ssize_t n = send(fd, buf + off, len - off, 0);
		if (n <= 0)
			return -1;
		off += (size_t)n;
	}
	return 0;
}

int main(int argc, char **argv)
{
	if (argc != 3) {
		fprintf(stderr, "usage: %s <port> <transcript-file>\n", argv[0]);
		return 2;
	}

	FILE *tr = fopen(argv[2], "w");
	if (!tr) {
		perror("fopen transcript");
		return 2;
	}

	int ls = socket(AF_INET, SOCK_STREAM, 0);
	if (ls < 0) {
		perror("socket");
		fclose(tr);
		return 2;
	}

	int one = 1;
	setsockopt(ls, SOL_SOCKET, SO_REUSEADDR, &one, sizeof one);

	struct sockaddr_in addr;
	memset(&addr, 0, sizeof addr);
	addr.sin_family = AF_INET;
	addr.sin_port = htons((unsigned short)atoi(argv[1]));
	addr.sin_addr.s_addr = htonl(INADDR_LOOPBACK);

	if (bind(ls, (struct sockaddr *)&addr, sizeof addr) != 0) {
		perror("bind");
		close(ls);
		fclose(tr);
		return 2;
	}
	if (listen(ls, 1) != 0) {
		perror("listen");
		close(ls);
		fclose(tr);
		return 2;
	}

	/* Readiness marker for test.sh (printed before accepting). */
	printf("LISTENING %s\n", argv[1]);
	fflush(stdout);

	signal(SIGALRM, on_alarm);
	alarm(30);

	int c = accept(ls, NULL, NULL);
	if (c < 0) {
		if (timed_out)
			fprintf(stderr, "no connection within 30s\n");
		else
			perror("accept");
		close(ls);
		fclose(tr);
		return 3;
	}
	alarm(0);

	if (send_all(c, "220 mock ESMTP ready\r\n") != 0) {
		close(c);
		close(ls);
		fclose(tr);
		return 4;
	}

	char line[4096];
	size_t used = 0;
	int quit = 0;

	while (!quit) {
		char chunk[1024];
		ssize_t n = recv(c, chunk, sizeof chunk, 0);
		if (n <= 0)
			break;

		for (ssize_t i = 0; i < n; i++) {
			char ch = chunk[i];
			if (used + 1 >= sizeof line)
				used = 0; /* oversized line: drop */
			line[used++] = ch;
			if (ch != '\n')
				continue;

			line[used] = '\0';
			used = 0;

			char *p = line;
			while (*p == '\r' || *p == '\n')
				p++;
			char *e = p + strlen(p);
			while (e > p && (e[-1] == '\r' || e[-1] == '\n'))
				*--e = '\0';

			fprintf(tr, "%s\n", p);
			fflush(tr);

			if (strncasecmp(p, "EHLO", 4) == 0 || strncasecmp(p, "HELO", 4) == 0) {
				if (send_all(c, "250 mock\r\n") != 0)
					goto done;
			} else if (strncasecmp(p, "MAIL", 4) == 0 || strncasecmp(p, "RCPT", 4) == 0) {
				if (send_all(c, "250 OK\r\n") != 0)
					goto done;
			} else if (strcmp(p, "DATA") == 0) {
				if (send_all(c, "354 End data with <CR><LF>.<CR><LF>\r\n") != 0)
					goto done;
			} else if (strcmp(p, ".") == 0) {
				if (send_all(c, "250 OK: queued\r\n") != 0)
					goto done;
			} else if (strncasecmp(p, "QUIT", 4) == 0) {
				if (send_all(c, "221 Bye\r\n") != 0)
					goto done;
				quit = 1;
			}
		}
	}

done:
	close(c);
	close(ls);
	fclose(tr);
	return quit ? 0 : 4;
}
