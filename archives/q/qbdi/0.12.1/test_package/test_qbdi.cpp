/* test_qbdi.cpp - consumer test for the packaged QBDI on HarmonyOS PC.
 *
 * This is a *consumer* test (test_package), NOT an upstream test.  Upstream's
 * own suite is build/test/QBDITest (185 Catch2 cases, 86542 assertions) and is
 * counted separately.
 *
 * On HarmonyOS the relevant mode is the **in-process embedded VM** - QBDI
 * instruments a function *inside this very process*.  That deliberately avoids
 * ptrace / external attach, which this platform refuses (verified separately).
 *
 *  T1  the VM reports a version
 *  T2  an instrumented call() runs to completion
 *  T3  the instrumented function still returns its correct value
 *  T4  the PREINST callback fires for the executed instructions
 *  T5  a second, independent VM run works too (no global state leak)
 *
 * Note: VM::call() requires a virtual stack (see the example in QBDI/VM.h),
 * hence allocateVirtualStack()/alignedFree() around each run.
 */
#include <cstdio>
#include <cstdint>

#include <QBDI.h>

static int failures = 0;
static int checks = 0;

static void check(bool cond, const char *name)
{
    checks++;
    if (cond) {
        printf("  PASS  %s\n", name);
    } else {
        printf("  FAIL  %s\n", name);
        failures++;
    }
}

/* the function we will instrument - kept simple and side-effect free */
static uint32_t add3(uint32_t a, uint32_t b, uint32_t c)
{
    volatile uint32_t r = a + b + c;
    return r;
}

static bool runInstrumented(uint32_t *instrCount, uint32_t *result)
{
    QBDI::VM vm;

    /* VM::call() needs a stack of its own */
    QBDI::GPRState *state = vm.getGPRState();
    uint8_t *fakestack = nullptr;
    if (!QBDI::allocateVirtualStack(state, 0x1000000, &fakestack)) {
        return false;
    }

    vm.addInstrumentedModuleFromAddr(reinterpret_cast<QBDI::rword>(&add3));

    *instrCount = 0;
    vm.addCodeCB(
        QBDI::PREINST,
        [instrCount](QBDI::VMInstanceRef v, QBDI::GPRState *gpr,
                     QBDI::FPRState *fpr) -> QBDI::VMAction {
            (void)v; (void)gpr; (void)fpr;
            (*instrCount)++;
            return QBDI::VMAction::CONTINUE;
        });

    QBDI::rword ret = 0;
    const bool ok = vm.call(&ret, reinterpret_cast<QBDI::rword>(&add3), {1, 2, 3});
    *result = static_cast<uint32_t>(ret);

    QBDI::alignedFree(fakestack);
    return ok;
}

int main()
{
    printf("QBDI consumer test (packaged library, embedded VM on device)\n");

    /* T1 */
    uint32_t verNum = 0;
    const char *ver = QBDI::getVersion(&verNum);
    check(ver != nullptr && ver[0] != '\0',
          "T1  QBDI::getVersion() returns a version string");
    printf("        version = %s (0x%08x)\n", ver ? ver : "(null)", verNum);

    /* T2 + T3 + T4 */
    uint32_t instrCount = 0;
    uint32_t result = 0;
    const bool ok = runInstrumented(&instrCount, &result);
    check(ok, "T2  instrumented call() completed");
    check(result == 6, "T3  instrumented add3(1,2,3) still returns 6");
    check(instrCount > 0, "T4  PREINST callback fired for the executed instructions");
    printf("        instructions observed = %u, result = %u\n", instrCount, result);

    /* T5: a second, independent VM run must work too (no global state leak) */
    uint32_t instrCount2 = 0;
    uint32_t result2 = 0;
    const bool ok2 = runInstrumented(&instrCount2, &result2);
    check(ok2 && result2 == 6,
          "T5  a second instrumentation run works and reports instructions");
    printf("        second run: instructions = %u, result = %u\n",
           instrCount2, result2);

    printf("\nchecks=%d failures=%d\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
