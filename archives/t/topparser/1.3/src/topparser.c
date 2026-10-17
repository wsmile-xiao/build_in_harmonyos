/*
 * topparser.c — implementation of the topparser library.
 *
 * Parses the output of the Linux `top -b -n 1` command into structured data.
 * Implementation is deliberately dependency-free and uses only POSIX libc
 * facilities (available on the HarmonyOS PC musl toolchain).
 *
 * License: MIT
 */
#define _POSIX_C_SOURCE 200809L

#include "topparser.h"

#include <ctype.h>
#include <errno.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

/* ------------------------------------------------------------------ */
/* helpers                                                            */
/* ------------------------------------------------------------------ */

static double parse_pct(const char *tok)
{
    /* Accept "17.5us", "17.5 us", "0.0", "-". */
    char *end = NULL;
    double v;

    if (tok == NULL || *tok == '\0' || *tok == '-' || *tok == '?')
        return 0.0;
    errno = 0;
    v = strtod(tok, &end);
    if (errno != 0 || end == tok)
        return 0.0;
    return v;
}

/* Trim leading and trailing whitespace in place. Returns pointer to start. */
static char *trim(char *s)
{
    char *end;

    while (*s && isspace((unsigned char)*s))
        s++;
    end = s + strlen(s);
    while (end > s && isspace((unsigned char)end[-1]))
        end--;
    *end = '\0';
    return s;
}

/* Copy at most n-1 bytes, guaranteeing NUL termination. */
static void copy_field(char *dst, size_t n, const char *src)
{
    if (n == 0)
        return;
    snprintf(dst, n, "%s", src ? src : "");
}

/* Split a line into whitespace-separated tokens, up to max_toks. */
static int split_tokens(char *line, char **toks, int max_toks)
{
    int n = 0;
    char *p = line;

    while (n < max_toks) {
        while (*p && isspace((unsigned char)*p))
            p++;
        if (*p == '\0')
            break;
        toks[n++] = p;
        while (*p && !isspace((unsigned char)*p))
            p++;
        if (*p)
            *p++ = '\0';
    }
    return n;
}

static int ensure_processes(topparser_result_t *out)
{
    size_t newcap;

    if (out->processes == NULL) {
        newcap = 64;
        out->processes = (topparser_process_t *)malloc(sizeof(topparser_process_t) * newcap);
        if (out->processes == NULL)
            return -1;
        out->cap = newcap;
        return 0;
    }
    if (out->nprocesses >= out->cap) {
        topparser_process_t *np;
        newcap = out->cap * 2;
        np = (topparser_process_t *)realloc(out->processes, sizeof(topparser_process_t) * newcap);
        if (np == NULL)
            return -1;
        out->processes = np;
        out->cap = newcap;
    }
    return 0;
}

/* ------------------------------------------------------------------ */
/* block parsers                                                      */
/* ------------------------------------------------------------------ */

/*
 * "top - 09:26:23 up 2:21,  1 user,  load average: 0.52, 0.58, 0.59"
 */
static void parse_summary(topparser_summary_t *s, const char *line)
{
    const char *p;
    int idx = 0;

    memset(s, 0, sizeof(*s));

    /* wall-clock time follows "top - " */
    p = line;
    while (*p && isspace((unsigned char)*p))
        p++;
    p = strstr(p, " - ");
    if (p)
        p += 3;                /* skip ": HH:MM:SS ..." leading space? no: " - " -> past it */
    while (p && *p && isspace((unsigned char)*p))
        p++;
    if (p && *p) {
        const char *sp = p;
        while (*sp && !isspace((unsigned char)*sp) && *sp != ',')
            sp++;
        {
            size_t len = (size_t)(sp - p);
            if (len >= sizeof(s->time))
                len = sizeof(s->time) - 1;
            snprintf(s->time, sizeof(s->time), "%.*s", (int)len, p);
        }
    }

    /* "up 2:21," or "up 3 days, 1:05," */
    p = strstr(line, " up ");
    if (p) {
        const char *comma = strchr(p + 4, ',');
        size_t len = comma ? (size_t)(comma - (p + 4)) : strlen(p + 4);
        if (len >= sizeof(s->up))
            len = sizeof(s->up) - 1;
        snprintf(s->up, sizeof(s->up), "%.*s", (int)len, p + 4);
    }

    /* "1 user" / "N users" */
    p = strstr(line, " user");
    if (p) {
        const char *start = p - 1;
        while (start > line && isdigit((unsigned char)start[-1]))
            start--;
        s->users = (int)strtol(start, NULL, 10);
    }

    /* "load average: 0.52, 0.58, 0.59" */
    p = strstr(line, "load average:");
    if (p) {
        const char *q = p + strlen("load average:");
        while (*q == ' ' || *q == ':')
            q++;
        while (*q != '\0' && idx < 3) {
            s->loadavg[idx++] = strtod(q, (char **)&q);
            while (*q == ' ' || *q == ',')
                q++;
        }
    }
}

/*
 * "Tasks:  17 total,   1 running,  16 sleeping,   0 stopped,   0 zombie"
 */
static void parse_tasks(topparser_tasks_t *t, const char *line)
{
    const char *p;

    memset(t, 0, sizeof(*t));

    p = strstr(line, "total");
    if (p)
        t->total = (int)strtol(strstr(line, ":") ? strstr(line, ":") + 1 : line, NULL, 10);

    if ((p = strstr(line, "running"))) {
        char *start = (char *)p - 1;
        while (start > line && isdigit((unsigned char)start[-1]))
            start--;
        t->running = (int)strtol(start, NULL, 10);
    }
    if ((p = strstr(line, "sleeping"))) {
        char *start = (char *)p - 1;
        while (start > line && isdigit((unsigned char)start[-1]))
            start--;
        t->sleeping = (int)strtol(start, NULL, 10);
    }
    if ((p = strstr(line, "stopped"))) {
        char *start = (char *)p - 1;
        while (start > line && isdigit((unsigned char)start[-1]))
            start--;
        t->stopped = (int)strtol(start, NULL, 10);
    }
    if ((p = strstr(line, "zombie"))) {
        char *start = (char *)p - 1;
        while (start > line && isdigit((unsigned char)start[-1]))
            start--;
        t->zombie = (int)strtol(start, NULL, 10);
    }
}

/*
 * "%Cpu(s): 17.5 us,  4.7 sy,  0.0 ni, 77.5 id,  0.0 wa,  0.4 hi, 0.0 si, 0.0 st"
 */
static void parse_cpu(topparser_cpu_t *c, const char *line)
{
    /* value followed by a two-letter suffix token, in order. */
    const char *suffixes[8] = { "us", "sy", "ni", "id", "wa", "hi", "si", "st" };
    double *targets[8] = { &c->us, &c->sy, &c->ni, &c->id, &c->wa, &c->hi, &c->si, &c->st };
    const char *p = strchr(line, ':');
    int i;

    memset(c, 0, sizeof(*c));
    if (p == NULL)
        return;
    p++;
    while (*p && isspace((unsigned char)*p))
        p++;

    for (i = 0; i < 8; i++) {
        char *found = (char *)p; /* linear scan for the suffix token */
        while (*found) {
            if (found[0] == suffixes[i][0] && found[1] == suffixes[i][1] &&
                (found == p || isspace((unsigned char)found[-1]))) {
                /* found points at the suffix; back up over any spaces and then
                 * over the numeric value that precedes it. */
                char *endv = found;
                char *startv;
                while (endv > p && isspace((unsigned char)endv[-1]))
                    endv--;
                startv = endv;
                while (startv > p && (isdigit((unsigned char)startv[-1]) || (unsigned char)startv[-1] == '.'))
                    startv--;
                *targets[i] = parse_pct(startv);
                break;
            }
            found++;
        }
    }
}

/*
 * One data row (procps "full" mode):
 * PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND
 * 1234 root      20   0  162796   8948   6684 S   0.0   0.1   0:00.20 bash
 */
static int parse_row(topparser_process_t *proc, char *line)
{
    char *toks[16];
    int n = split_tokens(line, toks, 16);

    if (n < 12)
        return -1; /* not a process row */

    memset(proc, 0, sizeof(*proc));
    proc->pid        = (int)strtol(toks[0], NULL, 10);
    copy_field(proc->user,    sizeof(proc->user),    toks[1]);
    copy_field(proc->pr,      sizeof(proc->pr),      toks[2]);
    copy_field(proc->ni,      sizeof(proc->ni),      toks[3]);
    copy_field(proc->virt,    sizeof(proc->virt),    toks[4]);
    copy_field(proc->res,     sizeof(proc->res),     toks[5]);
    copy_field(proc->shr,     sizeof(proc->shr),     toks[6]);
    copy_field(proc->s,       sizeof(proc->s),       toks[7]);
    proc->cpu        = parse_pct(toks[8]);
    proc->mem        = parse_pct(toks[9]);
    copy_field(proc->time,    sizeof(proc->time),    toks[10]);
    copy_field(proc->command, sizeof(proc->command), toks[11]);
    return 0;
}

/* ------------------------------------------------------------------ */
/* public API                                                         */
/* ------------------------------------------------------------------ */

int topparser_init(topparser_result_t *out)
{
    if (out == NULL)
        return -1;
    memset(out, 0, sizeof(*out));
    return 0;
}

int topparser_parse(topparser_result_t *out, const char *input)
{
    char *copy;
    char *save;
    char *line;

    if (out == NULL || input == NULL)
        return -1;

    copy = strdup(input);
    if (copy == NULL)
        return -1;

    save = NULL;
    for (line = strtok_r(copy, "\n", &save); line != NULL; line = strtok_r(NULL, "\n", &save)) {
        char *l = trim(line);

        if (l[0] == '\0')
            continue;

        if (strncmp(l, "top -", 5) == 0) {
            parse_summary(&out->summary, l);
        } else if (strncmp(l, "Tasks:", 6) == 0) {
            parse_tasks(&out->tasks, l);
        } else if (strncmp(l, "%Cpu", 4) == 0 || strncmp(l, "%CPU(" ,5) == 0) {
            parse_cpu(&out->cpu, l);
        } else if (isdigit((unsigned char)l[0])) {
            if (out->nprocesses < TOPPARSER_MAX_PROC &&
                ensure_processes(out) == 0 &&
                parse_row(&out->processes[out->nprocesses], l) == 0) {
                out->nprocesses++;
            }
        }
        /* other lines (header, blank, "Mem:", "Swap:") are ignored */
    }

    free(copy);
    return 0;
}

void topparser_free(topparser_result_t *out)
{
    if (out == NULL)
        return;
    free(out->processes);
    out->processes = NULL;
    out->nprocesses = 0;
    out->cap = 0;
}
