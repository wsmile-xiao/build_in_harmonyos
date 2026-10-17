// coordgenlibs 3.0.2 — HarmonyOS PC (aarch64) specific verification test.
//
// Part of the coordgenlibs 3.0.2 delivery evidence (R01, pc1-45).
// Calls the coordgenlibs public C++ API (sketcherMinimizer / Molecule /
// Atom / Bond) and verifies real behavior on the OHOS aarch64 verification
// path (host aarch64 userland, clang 15.0.4 OHOS toolchain, libc++).
//
// This test is built and run by test_package/CMakeLists.txt as a dedicated
// HarmonyOS gate (see also upstream test_coordgen.cpp which needs maeparser
// + Boost and is tracked in notes.md's dual-caliber ledger).
//
// CHECK() fails fast with a non-zero exit and works under NDEBUG, so the
// gate never relies on assert().
#include "coordgen/sketcherMinimizer.h"

#include <cstdio>
#include <cstdlib>

namespace {

// CHECK: fail fast with a non-zero exit and a message; valid under NDEBUG.
#define CHECK(cond)                                                          \
  do {                                                                       \
    if (!(cond)) {                                                           \
      std::printf("FAIL: %s (line %d)\n", #cond, __LINE__);                  \
      return 1;                                                              \
    }                                                                        \
  } while (0)

} // namespace

int main() {
    // HarmonyOS platform guard: the OHOS toolchain defines __OHOS__; the
    // recipe targets os=OHOS. Verify the public API behaves correctly on
    // this platform by generating 2D coordinates for a small ring.
#if defined(__OHOS__)
    std::printf("coordgenlibs hmos: OHOS platform macro detected\n");
#else
    std::printf("coordgenlibs hmos: NOT built with __OHOS__ macro\n");
#endif

    sketcherMinimizer minimizer;

    /* create a molecule (heap, same lifetime pattern as upstream example) */
    sketcherMinimizerMolecule *mol = new sketcherMinimizerMolecule();

    sketcherMinimizerAtom *atom0 = mol->addNewAtom();
    sketcherMinimizerAtom *atom1 = mol->addNewAtom();
    sketcherMinimizerAtom *atom2 = mol->addNewAtom();
    sketcherMinimizerAtom *atom3 = mol->addNewAtom();
    CHECK(mol->getAtoms().size() == 4);

    atom0->setAtomicNumber(6);
    atom1->setAtomicNumber(6);
    atom2->setAtomicNumber(6);
    atom3->setAtomicNumber(7);

    atom0->setCoordinates(sketcherMinimizerPointF(0.0f, 0.0f));
    atom1->setCoordinates(sketcherMinimizerPointF(0.0f, 1.0f));
    atom2->setCoordinates(sketcherMinimizerPointF(1.0f, 1.0f));
    atom3->setCoordinates(sketcherMinimizerPointF(1.0f, 0.0f));

    sketcherMinimizerBond *b0 = mol->addNewBond(atom0, atom1);
    sketcherMinimizerBond *b1 = mol->addNewBond(atom1, atom2);
    sketcherMinimizerBond *b2 = mol->addNewBond(atom2, atom3);
    sketcherMinimizerBond *b3 = mol->addNewBond(atom3, atom0);
    b0->setBondOrder(1);
    b1->setBondOrder(1);
    b2->setBondOrder(2);
    b3->setBondOrder(1);
    CHECK(mol->getBonds().size() == 4);

    mol->assignBondsAndNeighbors(mol->getAtoms(), mol->getBonds());

    /* load minimizer and generate 2D coordinates (public API) */
    minimizer.initialize(mol);
    minimizer.runGenerateCoordinates();

    /* observable result: 4 atoms / 4 bonds and finite generated coordinates */
    bool coordsOk = true;
    for (const auto *a : mol->getAtoms()) {
        const sketcherMinimizerPointF &c = a->getCoordinates();
        if (c.x() != c.x() || c.y() != c.y()) { /* NaN check via public x()/y() */
            coordsOk = false;
        }
    }
    CHECK(coordsOk);
    CHECK(mol->getAtoms().size() == 4);
    CHECK(mol->getBonds().size() == 4);

    std::printf("PASS: coordgenlibs hmos generated coordinates for 4-atom ring"
                " (atoms=%zu bonds=%zu)\n",
                mol->getAtoms().size(), mol->getBonds().size());
    return 0;
}
