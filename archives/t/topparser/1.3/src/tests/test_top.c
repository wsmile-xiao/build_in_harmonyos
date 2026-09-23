/*
 * test_top.c — self-test for the vendored topparser library.
 *
 * Runs a set of real assertions against representative `top -b` snapshots.
 * This is the library's OWN self-test (topparser has no authoritative upstream
 * project; see conanfile.py docstring / test_package/MANIFEST.yml); it is wired
 * to the source Makefile's `make test`/`make check` targets and is built and
 * run in conanfile.py build() as the source-side ("upstream") test suite for
 * this packaged library.  It emits an HMBS_UPSTREAM_TEST_RESULT JSON marker
 * summarising the run with the real discovered/passed counts.
 *
 * License: MIT
 */
#include "topparser.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

static int g_pass = 0;
static int g_fail = 0;

static void check(int cond, const char *name)
{
    if (cond) {
        g_pass++;
        printf("ok - %s\n", name);
    } else {
        g_fail++;
        printf("not ok - %s\n", name);
    }
}

static int near(double a, double b)
{
    return fabs(a - b) < 0.001;
}

static const char SAMPLE[] =
    "top - 09:26:23 up 2:21,  1 user,  load average: 0.52, 0.58, 0.59\n"
    "Tasks:  17 total,   1 running,  16 sleeping,   0 stopped,   0 zombie\n"
    "%Cpu(s): 17.5 us,  4.7 sy,  0.0 ni, 77.5 id,  0.0 wa,  0.4 hi, 0.0 si, 0.0 st\n"
    "MiB Mem :  32668.9 total,  15846.8 free,   1661.7 used,  15160.4 buff/cache\n"
    "MiB Swap:      0.0 total,      0.0 free,      0.0 used.  32668.9 avail Mem\n"
    "\n"
    "    PID USER      PR  NI    VIRT    RES    SHR S  %CPU  %MEM     TIME+ COMMAND\n"
    "   1234 root      20   0  162796   8948   6684 S   0.0   0.1   0:00.20 bash\n"
    "   5678 user1     20   0 1048576 204800  51200 R  12.5   0.6   1:02:03 myapp\n";

int main(void)
{
    topparser_result_t r;

    if (topparser_init(&r) != 0) {
        printf("FATAL - topparser_init failed\n");
        return 1;
    }

    if (topparser_parse(&r, SAMPLE) != 0) {
        printf("FATAL - topparser_parse failed\n");
        topparser_free(&r);
        return 1;
    }

    /* summary block */
    check(strncmp(r.summary.time, "09:26", 5) == 0, "summary.time parsed");
    check(strstr(r.summary.up, "2:21") != NULL,     "summary.up parsed");
    check(r.summary.users == 1,                     "summary.users parsed");

    /* load average */
    check(near(r.summary.loadavg[0], 0.52), "loadavg[0] == 0.52");
    check(near(r.summary.loadavg[1], 0.58), "loadavg[1] == 0.58");
    check(near(r.summary.loadavg[2], 0.59), "loadavg[2] == 0.59");

    /* tasks */
    check(r.tasks.total == 17,        "tasks.total == 17");
    check(r.tasks.running == 1,       "tasks.running == 1");
    check(r.tasks.sleeping == 16,     "tasks.sleeping == 16");
    check(r.tasks.stopped == 0,       "tasks.stopped == 0");
    check(r.tasks.zombie == 0,        "tasks.zombie == 0");

    /* cpu */
    check(near(r.cpu.us, 17.5), "cpu.us == 17.5");
    check(near(r.cpu.sy, 4.7),  "cpu.sy == 4.7");
    check(near(r.cpu.id, 77.5), "cpu.id == 77.5");

    /* processes */
    check(r.nprocesses == 2, "two process rows parsed");
    if (r.nprocesses == 2) {
        check(r.processes[0].pid == 1234, "proc[0].pid == 1234");
        check(strcmp(r.processes[0].user, "root") == 0, "proc[0].user == root");
        check(near(r.processes[0].cpu, 0.0), "proc[0].cpu parsed");

        check(r.processes[1].pid == 5678, "proc[1].pid == 5678");
        check(strcmp(r.processes[1].user, "user1") == 0, "proc[1].user == user1");
        check(near(r.processes[1].cpu, 12.5), "proc[1].cpu == 12.5");
        check(strcmp(r.processes[1].command, "myapp") == 0, "proc[1].command == myapp");
    }

    topparser_free(&r);

    printf("summary: %d passed, %d failed\n", g_pass, g_fail);
    printf("HMBS_UPSTREAM_TEST_RESULT={\"status\":\"%s\",\"framework\":\"custom\",\"command\":\"./tests/self\",\"discovered\":%d,\"executed\":%d,\"passed\":%d,\"failed\":%d,\"skipped\":0}\n",
           g_fail == 0 ? "passed" : "failed", g_pass + g_fail, g_pass + g_fail, g_pass, g_fail);

    return g_fail == 0 ? 0 : 1;
}
