/*
 * shed_pty.h - pseudo-terminal harness shared by the shed consumer tests.
 *
 * The packaged shed is started on a real pseudo terminal (24x80,
 * TERM=vt100, terminfo from the ncurses package run environment).  Every
 * byte it prints is fed into a small VT100 screen model, so the tests can
 * wait for exact screen rows, type keys like a user and collect the exit
 * status.
 */
#ifndef SHED_PTY_H
#define SHED_PTY_H

#include <dirent.h>
#include <errno.h>
#include <fcntl.h>
#include <poll.h>
#include <signal.h>
#include <stdarg.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/ioctl.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <termios.h>
#include <time.h>
#include <unistd.h>

#define SCR_ROWS 24
#define SCR_COLS 80
#define WAIT_MS 20000

/* ------------------------------------------------------------------ */
/* VT100 screen model                                                  */
/* ------------------------------------------------------------------ */

typedef struct {
    char cell[SCR_ROWS][SCR_COLS];
    int r, c, top, bot, save_r, save_c, wrap;
    int state; /* 0 text, 1 after ESC, 2 in CSI, 3 skip one byte */
    char par[64];
    int npar;
} screen_t;

static inline int clampi(int v, int lo, int hi)
{
    return v < lo ? lo : (v > hi ? hi : v);
}

static inline void scr_blank(screen_t *s, int row, int from, int to)
{
    if (from <= to)
        memset(&s->cell[row][from], ' ', (size_t)(to - from + 1));
}

static inline void scr_init(screen_t *s)
{
    memset(s, 0, sizeof *s);
    memset(s->cell, ' ', sizeof s->cell);
    s->bot = SCR_ROWS - 1;
}

/* scroll rows [from, bot] up by n (used by LF at the bottom margin, DL, SU) */
static inline void scr_scroll_up(screen_t *s, int from, int n)
{
    while (n-- > 0) {
        memmove(s->cell[from], s->cell[from + 1], (size_t)(s->bot - from) * SCR_COLS);
        scr_blank(s, s->bot, 0, SCR_COLS - 1);
    }
}

/* scroll rows [from, bot] down by n (RI at the top margin, IL, SD) */
static inline void scr_scroll_down(screen_t *s, int from, int n)
{
    while (n-- > 0) {
        memmove(s->cell[from + 1], s->cell[from], (size_t)(s->bot - from) * SCR_COLS);
        scr_blank(s, from, 0, SCR_COLS - 1);
    }
}

static inline void scr_linefeed(screen_t *s)
{
    s->wrap = 0;
    if (s->r == s->bot)
        scr_scroll_up(s, s->top, 1);
    else if (s->r < SCR_ROWS - 1)
        s->r++;
}

static inline void scr_put(screen_t *s, char ch)
{
    if (s->wrap) { /* xenl: wrap only when the next glyph arrives */
        s->c = 0;
        scr_linefeed(s);
    }
    s->cell[s->r][s->c] = ch;
    if (s->c == SCR_COLS - 1)
        s->wrap = 1;
    else
        s->c++;
}

static inline void scr_csi(screen_t *s, char final)
{
    int p[8] = {0}, n = 0, a, i;
    const char *q = s->par;

    if (*q == '?' || *q == '>' || *q == '=')
        q++;
    while (*q && n < 8) {
        p[n] = 0;
        while (*q >= '0' && *q <= '9')
            p[n] = p[n] * 10 + (*q++ - '0');
        n++;
        if (*q == ';')
            q++;
        else
            break;
    }
    a = (n > 0 && p[0] > 0) ? p[0] : 1;

    switch (final) {
    case 'A': s->wrap = 0; s->r = clampi(s->r - a, 0, SCR_ROWS - 1); break;
    case 'B': s->wrap = 0; s->r = clampi(s->r + a, 0, SCR_ROWS - 1); break;
    case 'C': s->wrap = 0; s->c = clampi(s->c + a, 0, SCR_COLS - 1); break;
    case 'D': s->wrap = 0; s->c = clampi(s->c - a, 0, SCR_COLS - 1); break;
    case 'H':
    case 'f':
        s->wrap = 0;
        s->r = clampi(((n > 0 && p[0] > 0) ? p[0] : 1) - 1, 0, SCR_ROWS - 1);
        s->c = clampi(((n > 1 && p[1] > 0) ? p[1] : 1) - 1, 0, SCR_COLS - 1);
        break;
    case 'd': s->wrap = 0; s->r = clampi(a - 1, 0, SCR_ROWS - 1); break;
    case 'G':
    case '`': s->wrap = 0; s->c = clampi(a - 1, 0, SCR_COLS - 1); break;
    case 'J': /* erase in display */
        s->wrap = 0;
        if (n == 0 || p[0] == 0) {
            scr_blank(s, s->r, s->c, SCR_COLS - 1);
            for (i = s->r + 1; i < SCR_ROWS; i++)
                scr_blank(s, i, 0, SCR_COLS - 1);
        } else if (p[0] == 1) {
            for (i = 0; i < s->r; i++)
                scr_blank(s, i, 0, SCR_COLS - 1);
            scr_blank(s, s->r, 0, s->c);
        } else {
            for (i = 0; i < SCR_ROWS; i++)
                scr_blank(s, i, 0, SCR_COLS - 1);
        }
        break;
    case 'K': /* erase in line */
        s->wrap = 0;
        if (n == 0 || p[0] == 0)
            scr_blank(s, s->r, s->c, SCR_COLS - 1);
        else if (p[0] == 1)
            scr_blank(s, s->r, 0, s->c);
        else
            scr_blank(s, s->r, 0, SCR_COLS - 1);
        break;
    case 'X': /* erase characters */
        scr_blank(s, s->r, s->c, clampi(s->c + a - 1, 0, SCR_COLS - 1));
        break;
    case '@': /* insert blanks */
        a = clampi(a, 0, SCR_COLS - s->c);
        memmove(&s->cell[s->r][s->c + a], &s->cell[s->r][s->c], (size_t)(SCR_COLS - s->c - a));
        scr_blank(s, s->r, s->c, s->c + a - 1);
        break;
    case 'P': /* delete characters */
        a = clampi(a, 0, SCR_COLS - s->c);
        memmove(&s->cell[s->r][s->c], &s->cell[s->r][s->c + a], (size_t)(SCR_COLS - s->c - a));
        scr_blank(s, s->r, SCR_COLS - a, SCR_COLS - 1);
        break;
    case 'L':
        if (s->r >= s->top && s->r <= s->bot)
            scr_scroll_down(s, s->r, a);
        break;
    case 'M':
        if (s->r >= s->top && s->r <= s->bot)
            scr_scroll_up(s, s->r, a);
        break;
    case 'S': scr_scroll_up(s, s->top, a); break;
    case 'T': scr_scroll_down(s, s->top, a); break;
    case 'r': /* scrolling region; homes the cursor */
        s->top = clampi(((n > 0 && p[0] > 0) ? p[0] : 1) - 1, 0, SCR_ROWS - 1);
        s->bot = clampi(((n > 1 && p[1] > 0) ? p[1] : SCR_ROWS) - 1, 0, SCR_ROWS - 1);
        if (s->top >= s->bot) {
            s->top = 0;
            s->bot = SCR_ROWS - 1;
        }
        s->r = 0;
        s->c = 0;
        s->wrap = 0;
        break;
    default: /* SGR, modes, tabs, reports: no effect on the text */
        break;
    }
}

static inline void scr_esc(screen_t *s, unsigned char ch)
{
    s->state = 0;
    switch (ch) {
    case '[': s->state = 2; s->npar = 0; s->par[0] = 0; break;
    case '(': case ')': case '*': case '+': case '#': s->state = 3; break;
    case '7': s->save_r = s->r; s->save_c = s->c; break;
    case '8': s->r = s->save_r; s->c = s->save_c; s->wrap = 0; break;
    case 'D': scr_linefeed(s); break;
    case 'E': s->c = 0; scr_linefeed(s); break;
    case 'M':
        s->wrap = 0;
        if (s->r == s->top)
            scr_scroll_down(s, s->top, 1);
        else if (s->r > 0)
            s->r--;
        break;
    case 'c': scr_init(s); break;
    default: break; /* keypad modes, tab set, ... */
    }
}

static inline void scr_feed(screen_t *s, const char *buf, size_t len)
{
    size_t i;

    for (i = 0; i < len; i++) {
        unsigned char ch = (unsigned char)buf[i];

        if (s->state == 1) {
            scr_esc(s, ch);
            continue;
        }
        if (s->state == 2) {
            if (ch >= 0x40 && ch <= 0x7e) {
                s->state = 0;
                scr_csi(s, (char)ch);
            } else if (ch == 0x1b) {
                s->state = 1;
            } else if (ch >= 0x20 && s->npar < (int)sizeof s->par - 1) {
                s->par[s->npar++] = (char)ch;
                s->par[s->npar] = 0;
            }
            continue;
        }
        if (s->state == 3) {
            s->state = 0;
            continue;
        }
        switch (ch) {
        case 0x1b: s->state = 1; break;
        case '\r': s->c = 0; s->wrap = 0; break;
        case '\n': case '\v': case '\f': scr_linefeed(s); break;
        case '\b': s->wrap = 0; if (s->c > 0) s->c--; break;
        case '\t': s->wrap = 0; s->c = clampi((s->c / 8 + 1) * 8, 0, SCR_COLS - 1); break;
        default:
            if (ch >= 0x20 && ch < 0x7f)
                scr_put(s, (char)ch);
            else if (ch >= 0x80)
                scr_put(s, '?');
            break; /* BEL, SO/SI, NUL padding */
        }
    }
}

/* row text with trailing blanks removed */
static inline void scr_row(const screen_t *s, int row, char *out)
{
    int n = SCR_COLS;

    memcpy(out, s->cell[row], SCR_COLS);
    while (n > 0 && out[n - 1] == ' ')
        n--;
    out[n] = 0;
}

static inline void scr_dump(const screen_t *s)
{
    char line[SCR_COLS + 1];
    int i;

    for (i = 0; i < SCR_ROWS; i++) {
        scr_row(s, i, line);
        printf("    |%02d| %s\n", i, line);
    }
}

/* ------------------------------------------------------------------ */
/* shed on a pseudo terminal                                           */
/* ------------------------------------------------------------------ */

typedef struct {
    pid_t pid;
    int master;
    screen_t scr;
    char log[8192]; /* first bytes printed, for messages outside curses */
    size_t loglen;
} term_t;

static inline long now_ms(void)
{
    struct timespec ts;

    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (long)ts.tv_sec * 1000L + ts.tv_nsec / 1000000L;
}

/*
 * Start argv[0] with stdout/stderr (and stdin unless stdin_fd >= 0) on a new
 * pseudo terminal that becomes its controlling tty.  TERM is vt100, LINES
 * and COLUMNS are dropped so the size comes from TIOCGWINSZ, and TMPDIR is
 * replaced when tmpdir is not NULL.
 */
static inline int term_spawn(term_t *t, char *const argv[], const char *cwd, int stdin_fd,
                      const char *tmpdir)
{
    struct winsize ws;
    char slave_name[128];
    const char *name;

    memset(t, 0, sizeof *t);
    scr_init(&t->scr);
    memset(&ws, 0, sizeof ws);
    ws.ws_row = SCR_ROWS;
    ws.ws_col = SCR_COLS;

    t->master = posix_openpt(O_RDWR | O_NOCTTY);
    if (t->master < 0 || grantpt(t->master) != 0 || unlockpt(t->master) != 0)
        return -1;
    name = ptsname(t->master);
    if (!name)
        return -1;
    snprintf(slave_name, sizeof slave_name, "%s", name);
    ioctl(t->master, TIOCSWINSZ, &ws);

    t->pid = fork();
    if (t->pid < 0)
        return -1;
    if (t->pid == 0) {
        int slave;

        setsid();
        slave = open(slave_name, O_RDWR);
        if (slave < 0)
            _exit(126);
        ioctl(slave, TIOCSCTTY, 0);
        ioctl(slave, TIOCSWINSZ, &ws);
        dup2(stdin_fd >= 0 ? stdin_fd : slave, STDIN_FILENO);
        dup2(slave, STDOUT_FILENO);
        dup2(slave, STDERR_FILENO);
        if (slave > STDERR_FILENO)
            close(slave);
        close(t->master);
        if (cwd && chdir(cwd) != 0)
            _exit(126);
        setenv("TERM", "vt100", 1);
        unsetenv("LINES");
        unsetenv("COLUMNS");
        if (tmpdir)
            setenv("TMPDIR", tmpdir, 1);
        execv(argv[0], argv);
        _exit(127);
    }
    return 0;
}

/* read output for up to ms milliseconds: bytes read, 0 on timeout, -1 at EOF */
static inline int term_pump(term_t *t, int ms)
{
    struct pollfd pfd;
    char buf[4096];
    ssize_t n;
    size_t room;

    pfd.fd = t->master;
    pfd.events = POLLIN;
    pfd.revents = 0;
    n = poll(&pfd, 1, ms);
    if (n < 0)
        return errno == EINTR ? 0 : -1;
    if (n == 0)
        return 0;
    n = read(t->master, buf, sizeof buf);
    if (n <= 0)
        return -1; /* EIO once every slave descriptor is closed */
    scr_feed(&t->scr, buf, (size_t)n);
    room = sizeof t->log - 1 - t->loglen;
    if (room > (size_t)n)
        room = (size_t)n;
    memcpy(t->log + t->loglen, buf, room);
    t->loglen += room;
    t->log[t->loglen] = 0;
    return (int)n;
}

enum { ROW_EQ, ROW_PREFIX };

static inline int row_match(const screen_t *s, int row, int how, const char *text)
{
    char line[SCR_COLS + 1];

    scr_row(s, row, line);
    if (how == ROW_EQ)
        return strcmp(line, text) == 0;
    return strncmp(line, text, strlen(text)) == 0;
}

/* wait until screen row `row` shows `text` (exactly or as a prefix) */
static inline int term_wait_row(term_t *t, int row, int how, const char *text)
{
    long end = now_ms() + WAIT_MS;

    for (;;) {
        long left;

        if (row_match(&t->scr, row, how, text))
            return 1;
        left = end - now_ms();
        if (left <= 0)
            return 0;
        if (term_pump(t, left < 100 ? (int)left : 100) < 0)
            return row_match(&t->scr, row, how, text);
    }
}

static inline int term_send(term_t *t, const char *keys)
{
    size_t n = strlen(keys);

    return write(t->master, keys, n) == (ssize_t)n ? 0 : -1;
}

/* drain output until the child exits; exit code, or -1 (killed/timeout) */
static inline int term_finish(term_t *t)
{
    long end = now_ms() + WAIT_MS;
    int st = 0;

    for (;;) {
        pid_t w = waitpid(t->pid, &st, WNOHANG);

        if (w == t->pid) {
            while (term_pump(t, 50) > 0)
                ;
            close(t->master);
            return WIFEXITED(st) ? WEXITSTATUS(st) : -1;
        }
        if (now_ms() > end) {
            kill(t->pid, SIGKILL);
            waitpid(t->pid, &st, 0);
            close(t->master);
            return -1;
        }
        if (term_pump(t, 50) < 0)
            usleep(20000);
    }
}

/* ------------------------------------------------------------------ */
/* small helpers                                                       */
/* ------------------------------------------------------------------ */

static int g_case_failures;

static inline void check(int cond, const char *fmt, ...)
{
    va_list ap;

    printf("    %s ", cond ? "ok  " : "FAIL");
    va_start(ap, fmt);
    vprintf(fmt, ap);
    va_end(ap);
    printf("\n");
    if (!cond)
        g_case_failures++;
}

/* run argv without a terminal, stdout+stderr captured; exit code or -1 */
static inline int run_capture(char *const argv[], char *out, size_t outsz)
{
    int p[2], st = 0;
    size_t len = 0;
    ssize_t n;
    pid_t pid;

    if (pipe(p) != 0)
        return -1;
    pid = fork();
    if (pid < 0)
        return -1;
    if (pid == 0) {
        int nul = open("/dev/null", O_RDONLY);

        if (nul >= 0)
            dup2(nul, STDIN_FILENO);
        dup2(p[1], STDOUT_FILENO);
        dup2(p[1], STDERR_FILENO);
        close(p[0]);
        close(p[1]);
        execv(argv[0], argv);
        _exit(127);
    }
    close(p[1]);
    while (len < outsz - 1 && (n = read(p[0], out + len, outsz - 1 - len)) > 0)
        len += (size_t)n;
    out[len] = 0;
    close(p[0]);
    waitpid(pid, &st, 0);
    return WIFEXITED(st) ? WEXITSTATUS(st) : -1;
}

static inline int write_file(const char *path, const unsigned char *data, size_t len)
{
    FILE *fp = fopen(path, "wb");
    int ok;

    if (!fp)
        return -1;
    ok = fwrite(data, 1, len, fp) == len;
    return (fclose(fp) == 0 && ok) ? 0 : -1;
}

/* whole file into buf; length or -1 */
static inline long read_file(const char *path, char *buf, size_t bufsz)
{
    FILE *fp = fopen(path, "rb");
    size_t n;

    if (!fp)
        return -1;
    n = fread(buf, 1, bufsz, fp);
    fclose(fp);
    return (long)n;
}

/* create dir (parent must exist) and remove the files left in it */
static inline int reset_dir(const char *path)
{
    char p[4096];
    struct dirent *e;
    DIR *d;

    if (mkdir(path, 0755) != 0 && errno != EEXIST)
        return -1;
    d = opendir(path);
    if (!d)
        return -1;
    while ((e = readdir(d)) != NULL) {
        if (strcmp(e->d_name, ".") == 0 || strcmp(e->d_name, "..") == 0)
            continue;
        snprintf(p, sizeof p, "%s/%s", path, e->d_name);
        unlink(p);
    }
    closedir(d);
    return 0;
}

static inline int dir_entries(const char *path)
{
    struct dirent *e;
    DIR *d = opendir(path);
    int n = 0;

    if (!d)
        return -1;
    while ((e = readdir(d)) != NULL)
        if (strcmp(e->d_name, ".") != 0 && strcmp(e->d_name, "..") != 0)
            n++;
    closedir(d);
    return n;
}

static inline const char *bin8(unsigned b, char *buf)
{
    int i;

    for (i = 0; i < 8; i++)
        buf[i] = ((b >> (7 - i)) & 1U) ? '1' : '0';
    buf[8] = 0;
    return buf;
}

/* the row shed draws for byte b at offset off (ascii column mode 0) */
static inline void expect_row(char *out, size_t outsz, int width, unsigned off, unsigned char b)
{
    char asc[4] = "   ", bits[9];

    if (b >= 32 && b <= 126)
        asc[1] = (char)b;
    snprintf(out, outsz, "%0*u: %s %02X  %03u %03o %s", width, off, asc, (unsigned)b,
             (unsigned)b, (unsigned)b, bin8(b, bits));
}

/* the status row: "<cursor>/<length> (dec)" right-aligned, ending at column 78 */
static inline void expect_status(char *out, size_t outsz, unsigned cursor, unsigned length)
{
    char text[64];

    snprintf(text, sizeof text, "%u/%u (dec)", cursor, length);
    snprintf(out, outsz, "%*s", SCR_COLS - 1, text);
}

#define STATUS_ROW (SCR_ROWS - 3)

#endif /* SHED_PTY_H */
