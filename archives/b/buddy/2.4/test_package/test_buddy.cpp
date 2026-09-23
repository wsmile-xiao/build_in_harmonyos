// test_buddy.cpp — Conan consumer test for buddy/2.4 (BuDDy BDD package).
//
// Exercises the public C core API, the C++ wrapper classes and the
// finite-domain (fdd/bvec) extensions of the library built and packaged by
// the recipe.  Every CHECK has a failure exit path (message + exit 1), so a
// silent pass-through is impossible.  All calls match the buddy 2.4 headers
// (bdd.h/bvec.h/fdd.h): bdd.h auto-defines CPLUSPLUS under __cplusplus and
// switches on the C++ wrapper classes.

#include "bdd.h"
#include "bvec.h"
#include "fdd.h"

#include <cstdio>
#include <cstdlib>

static int g_checks = 0;

#define CHECK(cond)                                                        \
    do {                                                                   \
        ++g_checks;                                                        \
        if (!(cond)) {                                                     \
            std::printf("CHECK FAILED at line %d: %s\n", __LINE__, #cond); \
            std::exit(1);                                                  \
        }                                                                  \
    } while (0)

// --- C core: variables, boolean algebra, sat counting, support sets ------
// (compiled through the bdd.h C++ wrappers: in C++ mode bdd.h rewrites
// bdd_ithvar/bdd_makeset to the class-returning forms, so the whole test
// uses the refcounted bdd type; node ids stay unique per BDD)
static void test_c_core_basics()
{
    // 1000-node table, 10000-node operator cache.
    CHECK(bdd_init(1000, 10000) == 0);
    bdd_setvarnum(8);
    CHECK(bdd_varnum() == 8);

    // bdd wrapper objects MUST be destroyed before bdd_done(); every test
    // keeps them inside a scope block that closes before kernel shutdown.
    {
        bdd x0 = bdd_ithvar(0);
        bdd x1 = bdd_ithvar(1);
        CHECK(x0.id() >= 2);  // terminal false=0, true=1; encoded vars start at 2
        CHECK(x1.id() != x0.id());

        bdd a = bdd_and(x0, x1);
        bdd o = bdd_or(x0, x1);
        bdd n = bdd_not(x0);
        bdd e = bdd_biimp(x0, x1);
        CHECK(a != bddfalse);
        CHECK(o != bddfalse);
        CHECK(n != bddfalse);

        CHECK(bdd_satcount(a) == 64.0);  // over ALL 8 vars: 1 assignment * 2^6
        CHECK(bdd_satcountset(a, bdd_support(a)) == 1.0);  // x0&x1: one assignment
        CHECK(bdd_satcountset(o, bdd_support(o)) == 3.0);  // x0|x1: three
        CHECK(bdd_satcountset(e, bdd_support(e)) == 2.0);  // x0<->x1: both equal

        // De Morgan, via unique-node identity.
        CHECK(bdd_not(o) == bdd_and(n, bdd_not(x1)));
        // Double negation.
        CHECK(!n == x0);

        // Support set of a == {x0, x1}, scanned back into an int array.
        bdd sup = bdd_support(a);
        CHECK(sup != bddfalse);
        int *sv = NULL;
        int sn = 0;
        CHECK(bdd_scanset(sup, sv, sn) == 0);
        CHECK(sn == 2);
        CHECK(sv != NULL && sv[0] == 0 && sv[1] == 1);
        CHECK(sup == bdd_makeset(sv, sn));
        free(sv);

        // One satisfying assignment exists.
        CHECK(bdd_satone(a) != bddfalse);
    }

    bdd_done();
}

// --- C++ wrapper classes: operators, refcounted values ------------------
static void test_cpp_wrapper()
{
    CHECK(bdd_init(1000, 10000) == 0);
    bdd_setvarnum(8);

    {
        bdd x = bdd_ithvar(2);
        bdd y = bdd_ithvar(5);
        bdd conj = x & y;
        bdd disj = x | y;
        bdd neg = !x;
        bdd excl = x ^ y;

        // NOTE: this is the second bdd_init/bdd_done cycle of the process.
        // buddy 2.4 carries an upstream defect: bdd_support() caches its
        // scratch buffer in a static whose size marker is not reset by
        // bdd_done(), so calling bdd_support() again in a same-varnum
        // session dereferences the freed buffer (see notes.md).  Later
        // sessions therefore build variable sets explicitly via
        // bdd_makeset() instead of bdd_support().
        int xy[2] = {2, 5};
        bdd xy_set = bdd_makeset(xy, 2);

        CHECK(conj != bddfalse);
        CHECK((conj & x) == conj);
        CHECK((disj | x) == disj);
        CHECK((!neg) == x);  // double negation returns the original function
        CHECK(bdd_satcountset(conj, xy_set) == 1.0);
        CHECK(bdd_satcountset(disj, xy_set) == 3.0);
        CHECK(bdd_satcountset(excl, xy_set) == 2.0);  // exactly one of x,y
        CHECK((x | !x) == bddtrue);
        CHECK((x & !x) == bddfalse);
        CHECK(conj.id() != disj.id());
    }

    bdd_done();
}

// --- Finite-domain extensions (fdd.h) -----------------------------------
static void test_fdd()
{
    CHECK(bdd_init(1000, 10000) == 0);

    int domains[2] = {256, 256};
    CHECK(fdd_extdomain(domains, 2) == 0);  // fresh kernel: vars start at 0
    CHECK(fdd_domainnum() == 2);
    CHECK(fdd_domainsize(0) == 256);  // domain size in values
    CHECK(fdd_domainsize(1) == 256);
    CHECK(fdd_varnum(0) == 8);        // 8 BDD variables encode the domain

    {
        bdd v0 = fdd_ithvar(0, 42);
        bdd v1 = fdd_ithvar(1, 42);
        CHECK(v0 != bddfalse);
        CHECK((v0 & v1) != bddfalse);          // 0:=42 AND 1:=42 satisfiable
        CHECK((v0 & fdd_ithvar(0, 43)) == bddfalse);  // one value per domain
        CHECK(fdd_scanvar(v0, 0) == 42);
        CHECK(fdd_scanvar(v1, 1) == 42);
    }

    bdd_done();
}

// --- Bit-vector arithmetic (bvec.h) -------------------------------------
static void test_bvec()
{
    CHECK(bdd_init(1000, 10000) == 0);
    bdd_setvarnum(8);
    CHECK(bdd_varnum() == 8);

    {
        // Constant arithmetic: 9 + 6 == 15 (all four bits true).
        bvec c9 = bvec_con(4, 9);
        bvec c6 = bvec_con(4, 6);
        CHECK(c9.bitnum() == 4);
        CHECK(bvec_isconst(c9) == 1);
        bvec sumc = bvec_add(c9, c6);
        CHECK(sumc.bitnum() == 4);
        CHECK(sumc[0] != bddfalse);
        CHECK(sumc[1] != bddfalse);
        CHECK(sumc[2] != bddfalse);
        CHECK(sumc[3] != bddfalse);
        CHECK(bvec_equ(sumc, bvec_con(4, 15)) != bddfalse);

        // Variable arithmetic stays non-constant.
        bvec v = bvec_var(4, 0, 1);
        CHECK(!bvec_isconst(v));
        bvec s = bvec_add(v, c6);
        CHECK(s.bitnum() == 4);
        CHECK(!bvec_isconst(s));
        CHECK((s == bvec_add(bvec_var(4, 0, 1), bvec_con(4, 6))) != bddfalse);
    }

    bdd_done();
}

// --- Variable reordering preserves semantics ----------------------------
static void test_reordering()
{
    CHECK(bdd_init(1000, 10000) == 0);
    bdd_setvarnum(8);

    {
        bdd f = bdd_ithvar(0) & (bdd_ithvar(1) | bdd_ithvar(2));
        int fvars[3] = {0, 1, 2};  // support of f, built explicitly (see the
                                   // bdd_support defect note in this file)
        bdd fset = bdd_makeset(fvars, 3);
        CHECK(bdd_satcountset(f, fset) == 3.0);
        CHECK(bdd_var(f) == 0);  // root splits on the outer conjunction

        CHECK(bdd_swapvar(1, 2) == 0);
        CHECK(bdd_satcountset(f, fset) == 3.0);  // invariant under reordering
    }

    bdd_done();
}

int main()
{
    test_c_core_basics();
    test_cpp_wrapper();
    test_fdd();
    test_bvec();
    test_reordering();
    std::printf("buddy consumer test: all %d checks passed\n", g_checks);
    return 0;
}
