/* Minimal FastCGI responder used to exercise the listener created by
 * spawn-fcgi.  In no-fork mode spawn-fcgi duplicates the listening socket to
 * fd 0 and execs this program, so the socket is already listening here. */
#include <errno.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/time.h>
#include <unistd.h>

#define FCGI_BEGIN_REQUEST 1
#define FCGI_END_REQUEST 3
#define FCGI_PARAMS 4
#define FCGI_STDIN 5
#define FCGI_STDOUT 6
#define FCGI_RESPONDER 1

static int read_exact(int fd, unsigned char *buffer, size_t length) {
    size_t offset = 0;
    while (offset < length) {
        ssize_t count = read(fd, buffer + offset, length - offset);
        if (count == 0) return 0;
        if (count < 0) {
            if (errno == EINTR) continue;
            return -1;
        }
        offset += (size_t)count;
    }
    return 1;
}

static int write_exact(int fd, const unsigned char *buffer, size_t length) {
    size_t offset = 0;
    while (offset < length) {
        ssize_t count = write(fd, buffer + offset, length - offset);
        if (count < 0) {
            if (errno == EINTR) continue;
            return -1;
        }
        offset += (size_t)count;
    }
    return 0;
}

static unsigned int read_u16(const unsigned char *buffer) {
    return ((unsigned int)buffer[0] << 8) | (unsigned int)buffer[1];
}

static int write_record(int fd, unsigned char type,
                        const unsigned char *body, unsigned int length) {
    unsigned char header[8];
    header[0] = 1;
    header[1] = type;
    header[2] = 0;
    header[3] = 1;
    header[4] = (unsigned char)((length >> 8) & 0xff);
    header[5] = (unsigned char)(length & 0xff);
    header[6] = 0;
    header[7] = 0;
    if (write_exact(fd, header, sizeof(header)) != 0) return -1;
    if (length && write_exact(fd, body, length) != 0) return -1;
    return 0;
}

int main(void) {
    static const unsigned char response[] =
        "Content-Type: text/plain\r\n"
        "Content-Length: 14\r\n"
        "\r\n"
        "spawn-fcgi-ok\n";
    unsigned char end_body[8] = {0, 0, 0, 0, 0, 0, 0, 0};
    unsigned char header[8];
    int client;
    int seen_begin = 0;
    int seen_params = 0;
    int seen_stdin = 0;
    int responder_role = 0;
    int record_count = 0;
    struct timeval timeout;

    timeout.tv_sec = 15;
    timeout.tv_usec = 0;
    alarm(20);

    client = accept(0, NULL, NULL);
    if (client < 0) {
        fprintf(stderr, "backend accept failed: %s\n", strerror(errno));
        return 10;
    }
    if (setsockopt(client, SOL_SOCKET, SO_RCVTIMEO,
                   &timeout, sizeof(timeout)) != 0) {
        fprintf(stderr, "backend setsockopt failed: %s\n", strerror(errno));
        return 11;
    }

    while (record_count++ < 256) {
        unsigned int content_length;
        unsigned int padding_length;
        unsigned char *body;
        int read_result = read_exact(client, header, sizeof(header));
        if (read_result <= 0) {
            fprintf(stderr, "backend failed to read FastCGI header\n");
            return 12;
        }
        if (header[0] != 1 || header[2] != 0 || header[3] != 1) {
            fprintf(stderr, "backend received invalid FastCGI header\n");
            return 13;
        }

        content_length = read_u16(header + 4);
        padding_length = header[6];
        body = NULL;
        if (content_length) {
            body = (unsigned char *)malloc(content_length + padding_length);
            if (!body) return 14;
            if (read_exact(client, body,
                           content_length + padding_length) <= 0) {
                free(body);
                return 15;
            }
        } else if (padding_length) {
            unsigned char padding[255];
            if (read_exact(client, padding, padding_length) <= 0) return 16;
        }

        if (header[1] == FCGI_BEGIN_REQUEST) {
            if (content_length != 8) return 17;
            responder_role = (int)read_u16(body);
            if (responder_role != FCGI_RESPONDER) return 18;
            seen_begin = 1;
        } else if (header[1] == FCGI_PARAMS) {
            if (content_length) seen_params = 1;
        } else if (header[1] == FCGI_STDIN) {
            if (content_length == 0) seen_stdin = 1;
        }
        free(body);

        if (seen_stdin) break;
    }

    if (!seen_begin || !seen_params || !seen_stdin) {
        fprintf(stderr, "backend missing records begin=%d params=%d stdin=%d\n",
                seen_begin, seen_params, seen_stdin);
        return 19;
    }

    if (write_record(client, FCGI_STDOUT, response,
                     (unsigned int)(sizeof(response) - 1)) != 0 ||
        write_record(client, FCGI_STDOUT, NULL, 0) != 0 ||
        write_record(client, FCGI_END_REQUEST, end_body,
                     sizeof(end_body)) != 0) {
        fprintf(stderr, "backend failed to write FastCGI response\n");
        return 20;
    }

    if (close(client) != 0) return 21;
    printf("FCGI_BACKEND_OK begin=%d params=%d stdin=%d role=%d\n",
           seen_begin, seen_params, seen_stdin, responder_role);
    fflush(stdout);
    return 0;
}
