/*
 * test_package consumer test — cmbacktrace 1.5.0
 *
 * Exercises the public API of the CmBackTrace library through its installed
 * headers and linked static library (R34: real API calls with observable
 * results, not a print-only stub):
 *   - cm_backtrace_init(): records firmware/hw/sw versions
 *   - cm_backtrace_firmware_info(): prints recorded versions (observable output)
 *   - cm_backtrace_call_stack(): returns backtrace depth (0 on OHOS aarch64 is
 *     expected: the Cortex-M BL/BLX semantics do not apply outside an MCU)
 */
#include <stdio.h>
#include <stdint.h>
#include <cm_backtrace.h>

int main(void) {
    uint32_t buf[8] = {0};

    cm_backtrace_init("cmbacktrace-consumer", "ohos-aarch64", "1.5.0");
    cm_backtrace_firmware_info();

    size_t depth = cm_backtrace_call_stack(buf, 8, (uint32_t)(uintptr_t)buf);
    printf("cm_backtrace_call_stack depth=%zu\n", depth);

    printf("cmbacktrace consumer test: OK\n");
    return 0;
}
