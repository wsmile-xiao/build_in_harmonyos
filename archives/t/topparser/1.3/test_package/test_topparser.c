/*
 * test_topparser.c — conan test_package consumer test for the topparser library.
 *
 * Verifies that a downstream consumer can include topparser.h, link against
 * libtopparser, and correctly parse a `top -b` snapshot via the public API.
 *
 * It also folds in the parsing assertions from the vendored library's own
 * self-test (src/tests/test_top.c) so the real parsing logic is exercised on
 * the target device.  NOTE: topparser has no authoritative upstream project
 * (see conanfile.py docstring); this is a consumer test of the vendored code,
 * not an upstream test suite.
 *
 * Emits HMBS_TEST_PACKAGE_RESULT with the real discovered/passed counts.
 */
#include "topparser.h"

#include <math.h>
#include <stdio.h>
#include <string.h>

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

static int g_case_count = 0;
static int g_case_pass = 0;

static void run_case(int cond, const char *name)
{
    g_case_count++;
    if (cond) {
        g_case_pass++;
        printf("ok - %s\n", name);
    } else {
        printf("not ok - %s\n", name);
    }
}

static int near(double a, double b)
{
    return fabs(a - b) < 0.001;
}

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

    /* Consumer linkage: public API structs/functions are usable. */
    run_case(TOPPARSER_VERSION_MAJOR == 1 && TOPPARSER_VERSION_MINOR == 3 &&
             strcmp(TOPPARSER_VERSION_STRING, "1.3") == 0,
             "version macros available to consumer");

    /* summary block */
    run_case(strncmp(r.summary.time, "09:26", 5) == 0, "summary.time parsed");
    run_case(strstr(r.summary.up, "2:21") != NULL,     "summary.up parsed");
    run_case(r.summary.users == 1,                     "summary.users parsed");

    /* load average */
    run_case(near(r.summary.loadavg[0], 0.52), "loadavg[0] == 0.52");
    run_case(near(r.summary.loadavg[1], 0.58), "loadavg[1] == 0.58");
    run_case(near(r.summary.loadavg[2], 0.59), "loadavg[2] == 0.59");

    /* tasks */
    run_case(r.tasks.total == 17,    "tasks.total == 17");
    run_case(r.tasks.running == 1,   "tasks.running == 1");
    run_case(r.tasks.sleeping == 16, "tasks.sleeping == 16");
    run_case(r.tasks.stopped == 0,   "tasks.stopped == 0");
    run_case(r.tasks.zombie == 0,    "tasks.zombie == 0");

    /* cpu */
    run_case(near(r.cpu.us, 17.5), "cpu.us == 17.5");
    run_case(near(r.cpu.sy, 4.7),  "cpu.sy == 4.7");
    run_case(near(r.cpu.id, 77.5), "cpu.id == 77.5");

    /* processes */
    run_case(r.nprocesses == 2, "two process rows parsed");
    if (r.nprocesses == 2) {
        run_case(r.processes[0].pid == 1234, "proc[0].pid == 1234");
        run_case(strcmp(r.processes[0].user, "root") == 0, "proc[0].user == root");
        run_case(near(r.processes[0].cpu, 0.0), "proc[0].cpu parsed");

        run_case(r.processes[1].pid == 5678, "proc[1].pid == 5678");
        run_case(strcmp(r.processes[1].user, "user1") == 0, "proc[1].user == user1");
        run_case(near(r.processes[1].cpu, 12.5), "proc[1].cpu == 12.5");
        run_case(strcmp(r.processes[1].command, "myapp") == 0, "proc[1].command == myapp");
    }
    topparser_free(&r);

    printf("summary: %d passed, %d failed\n", g_case_pass, g_case_count - g_case_pass);
    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,\"command\":\"./test_topparser\",\"discovered\":%d,\"passedCount\":%d}\n",
           g_case_pass == g_case_count ? "true" : "false",
           g_case_count, g_case_pass);

    return g_case_pass == g_case_count ? 0 : 1;
}
