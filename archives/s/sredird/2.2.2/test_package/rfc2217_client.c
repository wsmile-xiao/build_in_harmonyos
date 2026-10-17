/*
 * rfc2217_client - consumer of the sredird package (OHOS specific test).
 *
 * sredird has no library API; its interface is the Telnet/RFC 2217 byte stream
 * on stdin/stdout plus a serial device. This program is compiled with the OHOS
 * toolchain (musl), starts the *installed* bin/sredird with a socketpair as its
 * "inetd connection" and a pseudo terminal (posix_openpt) as its "serial port",
 * and then plays the RFC 2217 client:
 *
 *   T1  the initial Telnet negotiation (WILL/DO BINARY, WILL ECHO, WILL/DO SGA,
 *       DO COM-PORT) arrives byte-exact
 *   T2  the HDB lock file holds the sredird pid
 *   T3  network -> serial: bytes written to the socket reach the pty master,
 *       0xFF arrives un-escaped (IAC IAC -> 0xFF)
 *   T4  serial -> network: bytes written to the pty master come back on the
 *       socket, 0xFF is doubled (0xFF -> IAC IAC)
 *   T5  SET-BAUDRATE 115200 is acknowledged and cfgetospeed() on the pty
 *       slave (musl termios) reports B115200
 *   T6  SET-DATASIZE 8, SET-STOPSIZE 2 then 1 and SET-CONTROL XON/XOFF then
 *       "no flow control" are acknowledged and applied: the pty slave's
 *       c_cflag/c_iflag show CS8, CSTOPB set then cleared, IXON|IXOFF set then
 *       cleared (a pty always forces 8 data bits and no parity, so 7-bit and
 *       parity requests cannot be observed on it)
 *   T7  closing the connection makes sredird exit with status 0 and remove the
 *       lock file
 *
 * Usage: rfc2217_client /path/to/sredird
 * Exit status 0 = all checks passed; every failure prints "FAIL Tn: ..." and
 * exits 1. Files are only created under the current working directory.
 */
#define _XOPEN_SOURCE 700
#define _DEFAULT_SOURCE
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

#define IAC 255
#define SB 250
#define SE 240
#define WILL 251
#define DO 253
#define COMPORT 44

static pid_t child = -1;
static char lockpath[512];
static char workdir[] = "./sredird-test-XXXXXX";

static void fail(const char *test, const char *what)
{
    printf("FAIL %s: %s\n", test, what);
    fflush(stdout);
    if (child > 0) {
        kill(child, SIGKILL);
        waitpid(child, NULL, 0);
    }
    if (lockpath[0])
        unlink(lockpath);
    rmdir(workdir);
    exit(1);
}

static void pass(const char *test, const char *what)
{
    printf("PASS %s: %s\n", test, what);
    fflush(stdout);
}

static long now_ms(void)
{
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1000L + ts.tv_nsec / 1000000L;
}

/* Read from fd until exactly len bytes have arrived (or timeout). */
static int read_exact(int fd, unsigned char *buf, size_t len, int timeout_ms)
{
    size_t got = 0;
    long end = now_ms() + timeout_ms;
    while (got < len) {
        long left = end - now_ms();
        if (left <= 0)
            return -1;
        struct pollfd p = { fd, POLLIN, 0 };
        int r = poll(&p, 1, (int)left);
        if (r < 0 && errno == EINTR)
            continue;
        if (r <= 0)
            return -1;
        ssize_t n = read(fd, buf + got, len - got);
        if (n <= 0)
            return -1;
        got += (size_t)n;
    }
    return 0;
}

/*
 * Read len bytes of the network stream while dropping the asynchronous
 * "IAC SB COM-PORT NOTIFY-MODEMSTATE <state> IAC SE" reports that sredird
 * sends on its own once COM-PORT is enabled (RFC 2217 section 3.2); every other
 * byte is returned as it is on the wire. The filter state survives across calls.
 */
static int net_take(int fd, unsigned char *out, size_t len, int timeout_ms)
{
    static unsigned char held[8];
    static int hlen = 0;   /* bytes of a possible report held back (IAC SB 44 107) */
    static int body = -1;  /* -1: not inside a report; else 0..3 see below */
    size_t got = 0;
    long end = now_ms() + timeout_ms;

    while (got < len) {
        unsigned char b;
        long left = end - now_ms();
        if (left <= 0)
            return -1;
        struct pollfd p = { fd, POLLIN, 0 };
        int r = poll(&p, 1, (int)left);
        if (r < 0 && errno == EINTR)
            continue;
        if (r <= 0 || read(fd, &b, 1) != 1)
            return -1;

        if (body >= 0) { /* inside a report: value [IAC], then IAC SE */
            if (body == 0)
                body = (b == IAC) ? 1 : 2;
            else if (body == 1 && b == IAC)
                body = 2;
            else if (body == 2 && b == IAC)
                body = 3;
            else if (body == 3 && b == SE) {
                body = -1;
                hlen = 0;
            } else
                return -1; /* malformed report */
            continue;
        }
        static const unsigned char head[4] = { IAC, SB, COMPORT, 107 };
        if (hlen == 0 && b != IAC) {
            out[got++] = b;
            continue;
        }
        if (hlen == 1 && b == IAC) { /* IAC IAC = escaped data byte 0xFF, pass both */
            out[got++] = IAC;
            if (got < len)
                out[got++] = IAC;
            hlen = 0;
            continue;
        }
        if (b == head[hlen] || hlen == 0) {
            held[hlen++] = b;
            if (hlen == 4)
                body = 0;
            continue;
        }
        /* not a report: release the held bytes, then the current one */
        {
            int i;
            for (i = 0; i < hlen && got < len; i++)
                out[got++] = held[i];
            hlen = 0;
            if (got < len)
                out[got++] = b;
        }
    }
    return 0;
}

static void write_all(int fd, const unsigned char *buf, size_t len)
{
    while (len > 0) {
        ssize_t n = write(fd, buf, len);
        if (n < 0 && errno == EINTR)
            continue;
        if (n <= 0)
            fail("io", "write failed");
        buf += n;
        len -= (size_t)n;
    }
}

/* Send one COM-PORT subnegotiation and expect the matching acknowledgement:
 * IAC SB COM-PORT cmd+100 <value> IAC SE. */
static void comport_set(int sock, const char *test, unsigned char cmd,
                        const unsigned char *val, size_t vlen)
{
    unsigned char req[16], ack[16];
    size_t n = 0, i;
    req[n++] = IAC; req[n++] = SB; req[n++] = COMPORT; req[n++] = cmd;
    for (i = 0; i < vlen; i++)
        req[n++] = val[i];
    req[n++] = IAC; req[n++] = SE;
    write_all(sock, req, n);

    memcpy(ack, req, n);
    ack[3] = (unsigned char)(cmd + 100);
    unsigned char got[16];
    if (net_take(sock, got, n, 5000) != 0)
        fail(test, "no acknowledgement from sredird");
    if (memcmp(got, ack, n) != 0)
        fail(test, "acknowledgement differs from the requested value");
}

/* Poll the slave termios until pred is true (sredird applies it asynchronously). */
static int slave_wait(int slave, int (*pred)(const struct termios *))
{
    long end = now_ms() + 3000;
    struct termios t;
    while (now_ms() < end) {
        if (tcgetattr(slave, &t) == 0 && pred(&t))
            return 0;
        usleep(20000);
    }
    return -1;
}

static int is_115200(const struct termios *t)
{
    return cfgetospeed(t) == B115200 && cfgetispeed(t) == B115200;
}

static int is_cs8_2stop(const struct termios *t)
{
    return (t->c_cflag & CSIZE) == CS8 && (t->c_cflag & CSTOPB);
}

static int is_cs8_1stop(const struct termios *t)
{
    return (t->c_cflag & CSIZE) == CS8 && !(t->c_cflag & CSTOPB);
}

static int is_xonxoff(const struct termios *t)
{
    return (t->c_iflag & IXON) && (t->c_iflag & IXOFF);
}

static int is_no_flow(const struct termios *t)
{
    return !(t->c_iflag & (IXON | IXOFF));
}

int main(int argc, char **argv)
{
    char slavename[256];
    int master, slave, sv[2];
    unsigned char buf[64];

    if (argc != 2) {
        fprintf(stderr, "usage: %s /path/to/sredird\n", argv[0]);
        return 2;
    }
    alarm(120); /* the whole run must never hang a CI worker */
    signal(SIGPIPE, SIG_IGN);

    if (!mkdtemp(workdir))
        fail("setup", "mkdtemp failed (current directory not writable)");
    snprintf(lockpath, sizeof lockpath, "%s/LCK..pts", workdir);

    /* the "serial port": a pseudo terminal pair */
    master = posix_openpt(O_RDWR | O_NOCTTY);
    if (master < 0 || grantpt(master) != 0 || unlockpt(master) != 0)
        fail("setup", "posix_openpt/grantpt/unlockpt failed");
    const char *sn = ptsname(master);
    if (!sn)
        fail("setup", "ptsname failed");
    snprintf(slavename, sizeof slavename, "%s", sn);
    slave = open(slavename, O_RDWR | O_NOCTTY);
    if (slave < 0)
        fail("setup", "cannot open the pty slave");

    /* the "network": sredird reads and writes its connection on fd 0/1 */
    if (socketpair(AF_UNIX, SOCK_STREAM, 0, sv) != 0)
        fail("setup", "socketpair failed");

    child = fork();
    if (child < 0)
        fail("setup", "fork failed");
    if (child == 0) {
        dup2(sv[1], STDIN_FILENO);
        dup2(sv[1], STDOUT_FILENO);
        close(sv[0]);
        close(sv[1]);
        close(master);
        close(slave);
        /* log level 0 (no syslog), device, lock file, poll interval 20 ms */
        execl(argv[1], "sredird", "0", slavename, lockpath, "20", (char *)NULL);
        _exit(127);
    }
    close(sv[1]);
    int sock = sv[0];

    /* T1: initial Telnet negotiation, byte exact */
    static const unsigned char nego[] = {
        IAC, WILL, 0,   IAC, DO, 0,   IAC, WILL, 1,
        IAC, WILL, 3,   IAC, DO, 3,   IAC, DO, COMPORT
    };
    if (net_take(sock, buf, sizeof nego, 5000) != 0)
        fail("T1", "no Telnet negotiation from sredird");
    if (memcmp(buf, nego, sizeof nego) != 0)
        fail("T1", "negotiation bytes differ from WILL/DO BINARY, WILL ECHO, WILL/DO SGA, DO COM-PORT");
    pass("T1", "initial Telnet negotiation (18 bytes) byte-exact");

    /* the client accepts COM-PORT control, as RFC 2217 requires */
    static const unsigned char will_cp[] = { IAC, WILL, COMPORT };
    write_all(sock, will_cp, sizeof will_cp);

    /* T2: HDB lock file = 10 chars right-aligned pid + newline */
    {
        char expect[32], got[32] = { 0 };
        snprintf(expect, sizeof expect, "%10d\n", (int)child);
        int fd = open(lockpath, O_RDONLY);
        if (fd < 0)
            fail("T2", "lock file was not created");
        ssize_t n = read(fd, got, sizeof got - 1);
        close(fd);
        if (n != 11 || memcmp(got, expect, 11) != 0)
            fail("T2", "lock file content is not the HDB pid line of the sredird process");
        pass("T2", "HDB lock file holds the sredird pid");
    }

    /* T3: network -> serial, 0xFF escaped as IAC IAC on the wire */
    {
        static const unsigned char wire[] = { 'h', 'e', 'l', 'l', 'o', IAC, IAC, 0x01 };
        static const unsigned char dev[] = { 'h', 'e', 'l', 'l', 'o', 0xFF, 0x01 };
        write_all(sock, wire, sizeof wire);
        if (read_exact(master, buf, sizeof dev, 5000) != 0)
            fail("T3", "data did not reach the serial device");
        if (memcmp(buf, dev, sizeof dev) != 0)
            fail("T3", "serial device received different bytes");
        pass("T3", "network -> serial data delivered, IAC IAC unescaped to 0xFF");
    }

    /* T4: serial -> network, 0xFF doubled */
    {
        static const unsigned char dev[] = { 'w', 'o', 'r', 'l', 'd', 0xFF, '!' };
        static const unsigned char wire[] = { 'w', 'o', 'r', 'l', 'd', IAC, IAC, '!' };
        write_all(master, dev, sizeof dev);
        if (net_take(sock, buf, sizeof wire, 5000) != 0)
            fail("T4", "data from the serial device did not reach the network");
        if (memcmp(buf, wire, sizeof wire) != 0)
            fail("T4", "network received different bytes");
        pass("T4", "serial -> network data delivered, 0xFF escaped to IAC IAC");
    }

    /* T5: SET-BAUDRATE 115200 (RFC 2217 value is a 4 byte big-endian number) */
    {
        static const unsigned char baud[] = { 0x00, 0x01, 0xC2, 0x00 };
        comport_set(sock, "T5", 1, baud, sizeof baud);
        if (slave_wait(slave, is_115200) != 0)
            fail("T5", "pty slave termios did not change to B115200");
        pass("T5", "SET-BAUDRATE 115200 acknowledged and applied via termios");
    }

    /* T6: data size, stop bits and flow control (RFC 2217 values) */
    {
        static const unsigned char size8[] = { 8 };
        static const unsigned char stop2[] = { 2 };
        static const unsigned char stop1[] = { 1 };
        static const unsigned char xonxoff[] = { 2 };
        static const unsigned char noflow[] = { 1 };
        comport_set(sock, "T6", 2, size8, 1);
        comport_set(sock, "T6", 4, stop2, 1);
        if (slave_wait(slave, is_cs8_2stop) != 0)
            fail("T6", "pty slave termios did not change to CS8 + CSTOPB");
        comport_set(sock, "T6", 4, stop1, 1);
        if (slave_wait(slave, is_cs8_1stop) != 0)
            fail("T6", "pty slave termios did not clear CSTOPB");
        comport_set(sock, "T6", 5, xonxoff, 1);
        if (slave_wait(slave, is_xonxoff) != 0)
            fail("T6", "pty slave termios did not enable IXON|IXOFF");
        comport_set(sock, "T6", 5, noflow, 1);
        if (slave_wait(slave, is_no_flow) != 0)
            fail("T6", "pty slave termios did not clear IXON|IXOFF");
        pass("T6", "SET-DATASIZE/STOPSIZE/CONTROL acknowledged and applied via termios");
    }

    /* T7: connection closed -> sredird exits 0 and removes its lock file */
    {
        int status = 0;
        long end = now_ms() + 5000;
        pid_t r = 0;
        close(sock);
        while (now_ms() < end && (r = waitpid(child, &status, WNOHANG)) == 0)
            usleep(20000);
        if (r != child)
            fail("T7", "sredird did not exit after the connection was closed");
        child = -1;
        if (!WIFEXITED(status) || WEXITSTATUS(status) != 0)
            fail("T7", "sredird exited with a non-zero status");
        if (access(lockpath, F_OK) == 0)
            fail("T7", "lock file still present after exit");
        rmdir(workdir);
        pass("T7", "sredird exited with status 0 and removed the lock file");
    }

    printf("ALL PASSED (7 checks)\n");
    return 0;
}
