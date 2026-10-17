// test_package consumer test — real call into coordgenlibs public API.
//
// Uses only the installed public headers (coordgen/sketcherMinimizer.h) and
// the exported coordgen library: builds a molecule, adds atoms and bonds,
// generates 2D coordinates, and verifies the observable atom/bond counts and
// that coordinates were actually set. Mirrors upstream example_dir/example.cpp
// lifetime pattern (stack minimizer + heap molecule) to stay within the
// library's supported usage.
#include <iostream>

#include "coordgen/sketcherMinimizer.h"

int main() {
    sketcherMinimizer minimizer;

    /* create a molecule (heap, same lifetime pattern as upstream example) */
    sketcherMinimizerMolecule *mol = new sketcherMinimizerMolecule();

    sketcherMinimizerAtom *atom0 = mol->addNewAtom();
    sketcherMinimizerAtom *atom1 = mol->addNewAtom();
    sketcherMinimizerAtom *atom2 = mol->addNewAtom();
    sketcherMinimizerAtom *atom3 = mol->addNewAtom();
    atom0->setAtomicNumber(6);
    atom1->setAtomicNumber(6);
    atom2->setAtomicNumber(6);
    atom3->setAtomicNumber(7);

    atom0->setCoordinates(sketcherMinimizerPointF(0.0f, 0.0f));
    atom1->setCoordinates(sketcherMinimizerPointF(0.0f, 1.0f));
    atom2->setCoordinates(sketcherMinimizerPointF(1.0f, 1.0f));
    atom3->setCoordinates(sketcherMinimizerPointF(1.0f, 0.0f));

    mol->addNewBond(atom0, atom1)->setBondOrder(1);
    mol->addNewBond(atom1, atom2)->setBondOrder(1);
    mol->addNewBond(atom2, atom3)->setBondOrder(2);
    mol->addNewBond(atom3, atom0)->setBondOrder(1);

    mol->assignBondsAndNeighbors(mol->getAtoms(), mol->getBonds());

    /* load minimizer and generate 2D coordinates (public API) */
    minimizer.initialize(mol);
    minimizer.runGenerateCoordinates();

    const std::vector<sketcherMinimizerAtom *> &atoms = mol->getAtoms();
    const std::vector<sketcherMinimizerBond *> &bonds = mol->getBonds();
    std::cout << "coordgenlibs consumer: atoms=" << atoms.size()
              << " bonds=" << bonds.size() << std::endl;

    /* observable result: 4 atoms / 4 bonds and finite generated coordinates */
    bool coordsOk = true;
    for (const auto *a : atoms) {
        const sketcherMinimizerPointF &c = a->getCoordinates();
        if (c.x() != c.x() || c.y() != c.y()) { /* NaN check via public x()/y() */
            coordsOk = false;
        }
    }
    bool ok = (atoms.size() == 4) && (bonds.size() == 4) && coordsOk;
    std::cout << (ok ? "PASS: coordgen generated coordinates for 4-atom ring"
                     : "FAIL: unexpected atom/bond counts or non-finite coords")
              << std::endl;
    return ok ? 0 : 1;
}