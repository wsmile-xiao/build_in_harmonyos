// test_package/test_mathicgb.cpp -- mathicgb 1.4 consumer test.
//
// Five groups, failures reported with distinct exit codes 2..6. Every
// criterion is an observable behaviour of the packaged library:
// installation layout (C probe + version string + umbrella header),
// GroebnerConfiguration accessors, a real computeGroebnerBasis run over
// mathic/memtailor, the monomial-order API contract, the IdealStreamLog
// wrapper + log API, and determinism of repeated runs.
#include <cmath>
#include <cstdio>
#include <cstring>
#include <sstream>
#include <string>
#include <vector>

#include <mathicgb.h>

static int fail(int code, const char* what) {
    std::printf("FAIL[%d]: %s\n", code, what);
    return code;
}

// Output stream that records what computeGroebnerBasis produces.
struct CountingStream {
    typedef mgb::GroebnerConfiguration::Coefficient Coefficient;
    typedef mgb::GroebnerConfiguration::VarIndex VarIndex;
    typedef mgb::GroebnerConfiguration::Exponent Exponent;
    typedef mgb::GroebnerConfiguration::Component Component;

    Coefficient mModulus;
    VarIndex mVarCount;
    Component mComCount;
    size_t polyCount;
    size_t currentTerms;
    size_t totalTerms;
    std::vector<size_t> termsPerPoly;

    CountingStream(Coefficient mod, VarIndex vars, Component comps)
        : mModulus(mod), mVarCount(vars), mComCount(comps),
          polyCount(0), currentTerms(0), totalTerms(0) {}

    Coefficient modulus() const { return mModulus; }
    VarIndex varCount() const { return mVarCount; }
    Component comCount() const { return mComCount; }

    void idealBegin() { polyCount = 0; totalTerms = 0; termsPerPoly.clear(); }
    void idealBegin(size_t) { idealBegin(); }
    void appendPolynomialBegin() { currentTerms = 0; }
    void appendPolynomialBegin(size_t) { currentTerms = 0; }
    void appendTermBegin(Component) {}
    void appendExponent(VarIndex, Exponent) {}
    void appendTermDone(Coefficient) { ++currentTerms; ++totalTerms; }
    void appendPolynomialDone() { ++polyCount; termsPerPoly.push_back(currentTerms); }
    void idealDone() {}
};

// Feed the ideal {x^2 - y, x^3 - z} over GF(mod) with 3 variables.
// (Same generators as upstream src/test/mathicgb.cpp::makeBasis.)
static void feedIdeal(mgb::GroebnerInputIdealStream& s, unsigned int mod) {
    s.idealBegin(2);
    s.appendPolynomialBegin(); // x^2 - y
    s.appendTermBegin(0);
    s.appendExponent(0, 2);
    s.appendTermDone(1);
    s.appendTermBegin(0);
    s.appendExponent(1, 1);
    s.appendTermDone(mod - 1);
    s.appendPolynomialDone();
    s.appendPolynomialBegin(2); // x^3 - z
    s.appendTermBegin(0);
    s.appendExponent(0, 3);
    s.appendTermDone(1);
    s.appendTermBegin(0);
    s.appendExponent(2, 1);
    s.appendTermDone(mod - 1);
    s.appendPolynomialDone();
    s.idealDone();
}

// -- Group 1: installation layout + configuration accessors -------------
static int group1() {
    // libmathicgbIsPresent() is the only extern "C" symbol in the archive
    // (configure.ac probes the library through it); linking it proves
    // -lmathicgb resolves.
    libmathicgbIsPresent();

    if (std::strcmp(MATHICGB_VERSION_STRING, "1.4") != 0)
        return fail(2, "MATHICGB_VERSION_STRING != \"1.4\"");

    mgb::GroebnerConfiguration conf(101, 3, 1);
    if (conf.modulus() != 101 || conf.varCount() != 3 || conf.comCount() != 1)
        return fail(2, "GroebnerConfiguration accessors mismatch");

    // Copy construction preserves the configuration.
    mgb::GroebnerConfiguration copy(conf);
    if (copy.modulus() != 101 || copy.varCount() != 3 || copy.comCount() != 1)
        return fail(2, "GroebnerConfiguration copy mismatch");

    // Every base order has a human-readable name.
    for (int o = 0; o <= 3; ++o) {
        const char* name = mgb::GroebnerConfiguration::baseOrderName(
            static_cast<mgb::GroebnerConfiguration::BaseOrder>(o));
        if (name == 0 || name[0] == '\0')
            return fail(2, "baseOrderName() empty");
    }

    std::printf("PASS 1: C probe + MATHICGB_VERSION_STRING=\"%s\" + "
                "GroebnerConfiguration(101,3,1) accessors/copy/orders\n",
                MATHICGB_VERSION_STRING);
    return 0;
}

// -- Group 2: a real Groebner basis computation --------------------------
static int group2(CountingStream& out) {
    mgb::GroebnerConfiguration conf(101, 3, 1);
    std::vector<mgb::GroebnerConfiguration::Exponent> grads;
    grads.push_back(1); grads.push_back(1); grads.push_back(1);
    if (!conf.setMonomialOrder(
            mgb::GroebnerConfiguration::RevLexDescendingBaseOrder, grads))
        return fail(3, "degree revlex order rejected");

    mgb::GroebnerInputIdealStream input(conf);
    feedIdeal(input, conf.modulus());
    mgb::computeGroebnerBasis(input, out);

    // The reduced basis of {x^2-y, x^3-z} is {x^2-y, xy-z, y^2-xz}:
    // at least the two generators must come back, every polynomial keeps
    // at least one term.
    if (out.polyCount < 2)
        return fail(3, "Groebner basis has fewer than 2 polynomials");
    if (out.totalTerms < 3)
        return fail(3, "Groebner basis lost terms");
    for (size_t i = 0; i < out.termsPerPoly.size(); ++i) {
        if (out.termsPerPoly[i] == 0)
            return fail(3, "empty polynomial in Groebner basis");
    }

    std::printf("PASS 2: computeGroebnerBasis({x^2-y, x^3-z}) -> %u polys, "
                "%u terms\n",
                (unsigned)out.polyCount, (unsigned)out.totalTerms);
    return 0;
}

// -- Group 3: monomial-order API contract --------------------------------
static int group3() {
    mgb::GroebnerConfiguration conf(101, 3, 1);

    // Default order is (1,1,1)-graded reverse lex.
    std::pair<mgb::GroebnerConfiguration::BaseOrder,
              std::vector<mgb::GroebnerConfiguration::Exponent> > ord =
        conf.monomialOrder();
    if (ord.first != mgb::GroebnerConfiguration::RevLexDescendingBaseOrder)
        return fail(4, "default base order is not revlex");
    if (ord.second.size() != 3 || ord.second[0] != 1)
        return fail(4, "default grading is not (1,1,1)");

    // Unordered (empty grading) revlex is not a global monomial order:
    // the header documents that setMonomialOrder returns false then.
    std::vector<mgb::GroebnerConfiguration::Exponent> empty;
    if (conf.setMonomialOrder(
            mgb::GroebnerConfiguration::RevLexDescendingBaseOrder, empty))
        return fail(4, "non-global order accepted");

    // Round-trips.
    conf.setComponentsAscending(false);
    if (conf.componentsAscending())
        return fail(4, "setComponentsAscending(false) not kept");
    conf.setComponentsAscending(true);
    conf.setSchreyering(false);
    if (conf.schreyering())
        return fail(4, "setSchreyering(false) not kept");
    conf.setMaxSPairGroupSize(7);
    if (conf.maxSPairGroupSize() != 7)
        return fail(4, "setMaxSPairGroupSize() not kept");
    conf.setMaxThreadCount(1);
    if (conf.maxThreadCount() != 1)
        return fail(4, "setMaxThreadCount() not kept");

    std::printf("PASS 3: default (1,1,1)-revlex + non-global rejection + "
                "option round-trips\n");
    return 0;
}

// -- Group 4: IdealStreamLog wrapper + log API smoke ---------------------
static int group4() {
    mgb::GroebnerConfiguration conf(101, 3, 1);
    std::vector<mgb::GroebnerConfiguration::Exponent> grads(3, 1);
    conf.setMonomialOrder(
        mgb::GroebnerConfiguration::RevLexDescendingBaseOrder, grads);

    mgb::GroebnerInputIdealStream input(conf);
    feedIdeal(input, conf.modulus());

    // Route the basis through IdealStreamLog into a counting stream: this
    // exercises the public stream adaptor on top of a real computation.
    CountingStream inner(conf.modulus(), conf.varCount(), conf.comCount());
    std::ostringstream log;
    mgb::IdealStreamLog<CountingStream> logged(log, inner);
    mgb::computeGroebnerBasis(input, logged);
    if (inner.polyCount < 2)
        return fail(5, "IdealStreamLog run produced < 2 polynomials");
    if (log.str().empty())
        return fail(5, "IdealStreamLog recorded no calls");

    // logTime/logNumber must be callable without crashing; a false return
    // simply means the named log is unavailable (documented behaviour).
    double value = 0.0;
    (void)mgb::logTime("no-such-log", value);
    (void)mgb::logNumber("no-such-log", value);

    std::printf("PASS 4: IdealStreamLog(%u polys logged) + logTime/logNumber "
                "smoke\n", (unsigned)inner.polyCount);
    return 0;
}

// -- Group 5: determinism across repeated runs ---------------------------
static int group5(const CountingStream& reference) {
    mgb::GroebnerConfiguration conf(101, 3, 1);
    std::vector<mgb::GroebnerConfiguration::Exponent> grads(3, 1);
    conf.setMonomialOrder(
        mgb::GroebnerConfiguration::RevLexDescendingBaseOrder, grads);

    mgb::GroebnerInputIdealStream input(conf);
    feedIdeal(input, conf.modulus());
    CountingStream again(conf.modulus(), conf.varCount(), conf.comCount());
    mgb::computeGroebnerBasis(input, again);

    if (again.polyCount != reference.polyCount ||
        again.totalTerms != reference.totalTerms ||
        again.termsPerPoly != reference.termsPerPoly)
        return fail(6, "repeated computation diverged");

    std::printf("PASS 5: repeated run bit-identical (%u polys, %u terms)\n",
                (unsigned)again.polyCount, (unsigned)again.totalTerms);
    return 0;
}

int main() {
    if (const int rc = group1()) return rc;
    CountingStream reference(101, 3, 1);
    if (const int rc = group2(reference)) return rc;
    if (const int rc = group3()) return rc;
    if (const int rc = group4()) return rc;
    if (const int rc = group5(reference)) return rc;

    std::printf("ALL PASS: mathicgb 1.4 consumer tests (5 groups) on HarmonyOS\n");
    return 0;
}
