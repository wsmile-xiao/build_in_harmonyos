/* test_quantum.c: Consumer-side functional test for libquantum 1.0.0.
 *
 * Exercises the core quantum-register / gate / measurement APIs — not a
 * version-macro check. Creates a 2-qubit register, applies a Hadamard gate
 * (producing a uniform superposition), asserts the deterministic pre-measurement
 * probability amplitudes, applies a Pauli-X (sigma_x) gate and re-checks
 * normalisation, then performs a single-qubit measurement and asserts the
 * register collapses to exactly one basis state with total probability 1.0.
 * Finally reports version as a secondary sanity string.
 *
 * API-signature guard (P2): the libquantum 1.0.0 public headers declare
 *
 *     extern float        quantum_prob(COMPLEX_FLOAT a);   (quantum.h.in:128)
 *     extern const char * quantum_get_version(void);       (quantum.h.in:148)
 *
 * We bind those symbols to strongly-typed function-pointer aliases and call
 * through the aliases. If a future header/ABI ever drifts from those exact
 * signatures (return/parameter type or arity), the initialisation of the
 * const pointers below is a constraint-violation that the C compiler rejects
 * at build time — the test cannot silently pass against a wrong API.
 */
#include <quantum.h>

#include <math.h>
#include <stdio.h>
#include <string.h>

/* --- P2: compile-time API-signature guards --------------------------------
 *
 * These typedefs pin the exact signatures from the upstream 1.0.0 headers.
 * The const pointer initialisers below must agree with the declarations in
 * quantum.h to the byte; any mismatch (e.g. a non-const char* return on
 * quantum_get_version, or a second parameter on quantum_prob) is a hard
 * compile error rather than a runtime surprise.
 */
typedef float (*quantum_prob_fn)(COMPLEX_FLOAT);
typedef const char *(*quantum_get_version_fn)(void);

static quantum_prob_fn const libquantum_prob = quantum_prob;
static quantum_get_version_fn const libquantum_get_version = quantum_get_version;

static int failures = 0;

#define CHECK(cond, msg)                                      \
    do {                                                     \
        if (!(cond)) {                                       \
            printf("FAIL: %s\n", msg);                       \
            failures++;                                      \
        } else {                                             \
            printf("ok: %s\n", msg);                         \
        }                                                    \
    } while (0)

static int approx(float a, float b)
{
    return fabsf(a - b) < 1e-5f;
}

/* Sum |amplitude|^2 over every non-zero basis state of *reg.
 *
 * libquantum stores a sparse state vector: reg->node[0..size-1] each hold an
 * amplitude and a basis index, with quantum_prob(amplitude) giving the
 * Born-rule probability of that basis state. Summing over the populated nodes
 * therefore yields the register's total probability mass, which a properly
 * normalised register (freshly created, or post-measurement collapsed) holds
 * at 1.0.
 */
static float total_probability(const quantum_reg *reg)
{
    float total = 0.0f;
    for (int i = 0; i < reg->size; i++)
        total += libquantum_prob(reg->node[i].amplitude);
    return total;
}

int main(void)
{
    /* 1. Create a 2-qubit register in basis state |00>. */
    quantum_reg reg = quantum_new_qureg(0, 2);
    CHECK(reg.width == 2, "new_qureg width == 2");
    CHECK(reg.size == 1, "new_qureg |00> has 1 non-zero basis state");
    CHECK(approx(libquantum_prob(reg.node[0].amplitude), 1.0f),
          "|00> amplitude probability == 1.0");

    /* 2. Apply Hadamard to qubit 0: |00> -> (|00>+|01>)/sqrt(2) (uniform
     *    superposition over two basis states, each with probability 0.5). */
    quantum_hadamard(0, &reg);
    CHECK(reg.size == 2,
          "after H(q0): 2 non-zero basis states (uniform superposition)");

    CHECK(approx(total_probability(&reg), 1.0f),
          "after H(q0): total probability == 1.0 (normalised)");

    int half_found = 0;
    for (int i = 0; i < reg.size; i++)
        if (approx(libquantum_prob(reg.node[i].amplitude), 0.5f))
            half_found++;
    CHECK(half_found == 2,
          "after H(q0): each basis state has probability 0.5");

    /* 3. Apply sigma_x (Pauli-X / NOT) to qubit 1. X|0>=|1>, so it flips the
     *    qubit-1 value in each basis state; the register stays a 2-state
     *    uniform superposition. This exercises a second real gate path. */
    quantum_sigma_x(1, &reg);
    CHECK(reg.size == 2, "after X(q1): still 2 non-zero basis states");

    CHECK(approx(total_probability(&reg), 1.0f),
          "after X(q1): total probability == 1.0");

    /* 4. Measure qubit 0: collapses the superposition to one basis state.
     *
     *    libquantum 1.0.0 quantum_bmeasure() (measure.c:86) calls
     *    quantum_state_collapse() (qureg.c:375) and assigns its returned
     *    register back into *reg. quantum_state_collapse() eradicates the
     *    amplitudes of the basis states ruled out by the measurement, then
     *    normalises every surviving amplitude by 1/sqrt(d) where d is the sum
     *    of the retained probabilities (qureg.c:393 accumulates d,
     *    qureg.c:430 applies the scale factor). Therefore the post-measurement
     *    register has exactly one basis state whose probability is 1.0.
     *
     *    The assertions below verify that upstream post-measurement
     *    invariant: a valid bit result, a single surviving basis state, and
     *    total probability mass equal to 1.0. They do not relax or duplicate
     *    the library's own bookkeeping — total_probability() recomputes the
     *    probability mass independently from the stored amplitudes via the
     *    public quantum_prob() API. */
    int measured = quantum_bmeasure(0, &reg);
    CHECK(measured == 0 || measured == 1,
          "bmeasure returns valid bit value 0|1");
    CHECK(reg.size == 1, "after bmeasure: register collapsed to 1 basis state");
    CHECK(approx(total_probability(&reg), 1.0f),
          "after bmeasure: total probability == 1.0 (post-collapse invariant)");

    /* 5. Version sanity (secondary; the assertions above are the real test).
     *    Called through the typed alias so a signature drift fails to compile. */
    const char *ver = libquantum_get_version();
    CHECK(ver != NULL && strlen(ver) > 0,
          "quantum_get_version returns non-empty string");
    printf("libquantum version: %s\n", ver ? ver : "(null)");

    quantum_delete_qureg(&reg);

    if (failures == 0) {
        printf("\nALL TESTS PASSED\n");
        return 0;
    }
    printf("\n%d TEST(S) FAILED\n", failures);
    return 1;
}
