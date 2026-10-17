#include <rvvm/rvvmlib.h>
#include <stdint.h>
#include <stdio.h>

/* Consumer-side verification of the packaged librvvm public API (R34):
 * actually creates a machine and exercises the public entry points. */
int main(void) {
    const uint64_t magic = 0xDEADBEEFCAFEBABEULL;
    uint64_t got = 0;
    int rc = 0;

    rvvm_machine_t *machine = rvvm_create_machine(
        RVVM_DEFAULT_MEMBASE, 0x1000000, 1, true);
    if (!machine) {
        fprintf(stderr, "FAIL: rvvm_create_machine returned NULL\n");
        return 1;
    }

    if (!rvvm_write_ram(machine, RVVM_DEFAULT_MEMBASE, &magic, sizeof(magic))) {
        fprintf(stderr, "FAIL: rvvm_write_ram failed\n");
        rc = 1;
        goto out;
    }
    if (!rvvm_read_ram(machine, &got, RVVM_DEFAULT_MEMBASE, sizeof(got))) {
        fprintf(stderr, "FAIL: rvvm_read_ram failed\n");
        rc = 1;
        goto out;
    }
    if (got != magic) {
        fprintf(stderr, "FAIL: RAM round-trip mismatch (got 0x%llx)\n",
                (unsigned long long)got);
        rc = 1;
        goto out;
    }

    if (rvvm_get_opt(machine, RVVM_OPT_MEM_BASE) != RVVM_DEFAULT_MEMBASE) {
        fprintf(stderr, "FAIL: RVVM_OPT_MEM_BASE mismatch\n");
        rc = 1;
        goto out;
    }
    if (rvvm_get_opt(machine, RVVM_OPT_HART_COUNT) != 1) {
        fprintf(stderr, "FAIL: RVVM_OPT_HART_COUNT mismatch\n");
        rc = 1;
        goto out;
    }

    printf("rvvm 0.6 packaged API consumer test ok "
           "(create/write/read/mem_base/hart_count)\n");
out:
    rvvm_free_machine(machine);
    return rc;
}
