/*
 * libgtop consumer smoke test.
 *
 * Uses only the public installed headers (glibtop.h) and the public API to
 * verify a third-party consumer can compile, link, and call libgtop on
 * HarmonyOS: initialize the library and read the real CPU / memory / uptime
 * values from the running system.
 */
#include <stdio.h>
#include <stdlib.h>

#include <glibtop.h>
#include <glibtop/cpu.h>
#include <glibtop/mem.h>
#include <glibtop/uptime.h>

int main(void)
{
    glibtop *server;

    /* glibtop_init() returns a glibtop* (non-NULL on success). */
    server = glibtop_init();
    if (server == NULL) {
        fprintf(stderr, "glibtop_init failed\n");
        return 1;
    }

    glibtop_cpu cpu;
    glibtop_get_cpu(&cpu);
    if (cpu.total == 0) {
        fprintf(stderr, "glibtop_get_cpu returned zero total\n");
        glibtop_close();
        return 2;
    }

    glibtop_mem mem;
    glibtop_get_mem(&mem);
    if (mem.total == 0) {
        fprintf(stderr, "glibtop_get_mem returned zero total\n");
        glibtop_close();
        return 3;
    }

    glibtop_uptime up;
    glibtop_get_uptime(&up);
    if (up.uptime < 0.0) {
        fprintf(stderr, "glibtop_get_uptime returned negative uptime\n");
        glibtop_close();
        return 4;
    }

    printf("libgtop consumer OK: cpu_total=%llu mem_total=%llu mem_free=%llu uptime=%.1fs\n",
           (unsigned long long)cpu.total,
           (unsigned long long)mem.total,
           (unsigned long long)mem.free,
           up.uptime);

    glibtop_close();
    return 0;
}
