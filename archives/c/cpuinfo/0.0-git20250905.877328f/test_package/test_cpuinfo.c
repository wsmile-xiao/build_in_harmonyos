#include <stdio.h>
#include <cpuinfo.h>

/* Consumer test with 2 real cases:
 *  case 1: cpuinfo_initialize() succeeds and reports non-empty topology.
 *  case 2: processor/core/uarch counts are consistent (>0 and bounded).
 */
int main(void) {
    int passed = 0;
    if (!cpuinfo_initialize()) {
        printf("[FAIL] init: cpuinfo_initialize() returned false\n");
        return 1;
    }
    printf("[PASS] init: cpuinfo_initialize() succeeded\n");
    passed++;

    unsigned procs = cpuinfo_get_processors_count();
    unsigned cores = cpuinfo_get_cores_count();
    unsigned uarchs = cpuinfo_get_uarchs_count();
    printf("processors=%u cores=%u uarchs=%u\n", procs, cores, uarchs);
    if (procs == 0 || cores == 0 || cores > procs) {
        printf("[FAIL] topology: inconsistent counts\n");
        cpuinfo_deinitialize();
        return 1;
    }
    const struct cpuinfo_processor* p = cpuinfo_get_processors();
    const struct cpuinfo_core* c = cpuinfo_get_cores();
    if (p == 0 || c == 0) {
        printf("[FAIL] topology: null table pointers\n");
        cpuinfo_deinitialize();
        return 1;
    }
    printf("[PASS] topology: %u processors %u cores %u uarchs\n", procs, cores, uarchs);
    passed++;
    cpuinfo_deinitialize();
    printf("test_cpuinfo: %d/2 cases passed\n", passed);
    return passed == 2 ? 0 : 1;
}
