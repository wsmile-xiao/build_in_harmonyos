/*
 * topparser.h — public API for the topparser library.
 *
 * topparser is a small, dependency-free C library that parses the output of
 * the Linux `top -b` (batch mode) command into structured C data.
 *
 * License: MIT
 * Version: 1.3
 */
#ifndef TOPPARSER_H
#define TOPPARSER_H

#include <stddef.h>

#ifdef __cplusplus
extern "C" {
#endif

#define TOPPARSER_VERSION_MAJOR 1
#define TOPPARSER_VERSION_MINOR 3
#define TOPPARSER_VERSION_STRING "1.3"

#define TOPPARSER_MAX_CMD   256
#define TOPPARSER_MAX_USER   64
#define TOPPARSER_MAX_PID    32
#define TOPPARSER_MAX_PROC   4096

/* \brief Top-level summary block ("top - 09:26:23 up 2:21, ... load average: 0.52, 0.58, 0.59"). */
typedef struct {
    char    time[16];   /* wall-clock time reported by top            */
    char    up[16];     /* uptime string                              */
    int     users;      /* number of logged-in users                  */
    double  loadavg[3]; /* 1/5/15 minute load averages                */
} topparser_summary_t;

/* \brief "Tasks:" line counts. */
typedef struct {
    int total;
    int running;
    int sleeping;
    int stopped;
    int zombie;
} topparser_tasks_t;

/* \brief CPU percentage line ("%Cpu(s): 17.5 us, 4.7 sy, ..."). */
typedef struct {
    double us, sy, ni, id, wa, hi, si, st;
} topparser_cpu_t;

/* \brief One row of the per-process table. */
typedef struct {
    int         pid;
    char        user[TOPPARSER_MAX_USER];
    char        pr[8];
    char        ni[8];
    char        virt[32];
    char        res[32];
    char        shr[32];
    char        s[8];
    double      cpu;
    double      mem;
    char        time[16];
    char        command[TOPPARSER_MAX_CMD];
} topparser_process_t;

/* \brief A fully parsed snapshot of one `top -b` iteration. */
typedef struct {
    topparser_summary_t  summary;
    topparser_tasks_t    tasks;
    topparser_cpu_t      cpu;
    topparser_process_t *processes;   /* malloc'd array, nprocesses entries              */
    size_t               nprocesses;
    size_t               cap;         /* allocated capacity of processes                  */
} topparser_result_t;

/*
 * \brief Initialise a result structure to a clean state.
 * \return 0 on success, non-zero on allocation failure.
 */
int topparser_init(topparser_result_t *out);

/*
 * \brief Parse one `top -b` iteration snapshot.
 *
 * Parses the header/summary blocks and every data row of the process table.
 * Additional processes beyond TOPPARSER_MAX_PROC are ignored.
 *
 * \param out   Result structure previously initialised with topparser_init().
 * \param input NUL-terminated snapshot text produced by `top -b -n 1`.
 * \return 0 on success, non-zero on error. Partial results are retained.
 */
int topparser_parse(topparser_result_t *out, const char *input);

/*
 * \brief Release all resources owned by a result structure.
 */
void topparser_free(topparser_result_t *out);

#ifdef __cplusplus
}
#endif

#endif /* TOPPARSER_H */
