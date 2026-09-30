/* test_xbyak.cpp - consumer test for the packaged xbyak_aarch64 on HarmonyOS PC.
 *
 * This is a *consumer* test (test_package), NOT an upstream test.  Upstream's
 * own suite is test/test_all.sh (11 scenarios) plus test2/test_all.sh
 * (15 patterns) and is counted separately.
 *
 * What this proves on the real machine: the packaged library can JIT-emit
 * AArch64 machine code into a writable+executable buffer, flush the instruction
 * cache, and transfer control to it - i.e. the path-C claims about runtime code
 * generation, executable memory and cache maintenance all actually hold here.
 *
 *  T1  integer add emitted at run time, executed, result checked
 *  T2  branch/compare select emitted at run time, executed, result checked
 *  T3  NEON 4xint32 vector add emitted at run time, executed, result checked
 *  T4  generated encodings match the documented AArch64 opcodes
 *  T5  a longer generated sequence (mul + lsl) executes to the right result
 */
#include <cstdio>
#include <cstring>
#include <cstdint>

#include <xbyak_aarch64/xbyak_aarch64.h>

using namespace Xbyak_aarch64;

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

/* ---- T1: integer add ---------------------------------------------------- */
class AddGen : public CodeGenerator {
public:
    AddGen() {
        add(w0, w0, w1);   /* w0 = w0 + w1 */
        ret();
    }
};

/* ---- T2: a small loop/cmp-select function ------------------------------- */
/* int maxi(int a, int b) { return a > b ? a : b; } */
class MaxGen : public CodeGenerator {
public:
    MaxGen() {
        cmp(w0, w1);
        csel(w0, w0, w1, GT);
        ret();
    }
};

/* ---- T3: NEON ----------------------------------------------------------- */
/* void vadd4(int32_t *dst, const int32_t *a, const int32_t *b) {
 *     dst[0..3] = a[0..3] + b[0..3];
 * } */
class VAddGen : public CodeGenerator {
public:
    VAddGen() {
        ldr(q0, ptr(x1));
        ldr(q1, ptr(x2));
        add(VReg4S(0), VReg4S(0), VReg4S(1));
        str(q0, ptr(x0));
        ret();
    }
};

int main()
{
    printf("xbyak_aarch64 consumer test (packaged library, JIT on device)\n");

    /* T1 */
    {
        AddGen gen;
        gen.ready();
        auto f = gen.getCode<int (*)(int, int)>();
        int r = f(21, 21);
        check(r == 42, "T1  JIT-emitted add executes and returns 42");

        /* T4: 'add w0,w0,w1' is 0x0B010000 (little-endian 00 00 01 0B) */
        const uint8_t *p = reinterpret_cast<const uint8_t *>(f);
        uint32_t word = (uint32_t)p[0] | ((uint32_t)p[1] << 8) |
                        ((uint32_t)p[2] << 16) | ((uint32_t)p[3] << 24);
        check(word == 0x0B010000u,
              "T4a generated 'add w0,w0,w1' encoding is 0x0B010000");
    }

    /* T2 */
    {
        MaxGen gen;
        gen.ready();
        auto f = gen.getCode<int (*)(int, int)>();
        bool ok = (f(7, 3) == 7) && (f(3, 7) == 7) && (f(5, 5) == 5);
        check(ok, "T2  JIT-emitted cmp/csel selects the larger operand");
    }

    /* T3 */
    {
        VAddGen gen;
        gen.ready();
        auto f = gen.getCode<void (*)(int32_t *, const int32_t *, const int32_t *)>();
        int32_t a[4] = {1, 2, 3, 4};
        int32_t b[4] = {10, 20, 30, 40};
        int32_t d[4] = {0, 0, 0, 0};
        f(d, a, b);
        bool ok = d[0] == 11 && d[1] == 22 && d[2] == 33 && d[3] == 44;
        check(ok, "T3  JIT-emitted NEON vadd.4s computes [11,22,33,44]");
    }

    /* T5: a longer generated sequence - multiply then shift - proving the
       JIT buffer holds more than a single instruction and that the emitted
       code really runs. */
    {
        class MulShiftGen : public CodeGenerator {
        public:
            MulShiftGen() {
                mul(w0, w0, w1);   /* w0 = w0 * w1 */
                lsl(w0, w0, 1);    /* w0 <<= 1      */
                ret();
            }
        };
        MulShiftGen gen;
        gen.ready();
        auto f = gen.getCode<int (*)(int, int)>();
        check(f(6, 7) == 84, "T5  JIT-emitted mul+lsl sequence returns 84");
    }

    printf("\nchecks=%d failures=%d\n", checks, failures);
    return failures == 0 ? 0 : 1;
}
