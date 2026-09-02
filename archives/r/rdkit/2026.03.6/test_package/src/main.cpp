#include <GraphMol/RDKitBase.h>
#include <GraphMol/SmilesParse/SmilesParse.h>
#include <iostream>

int main() {
    auto mol = RDKit::SmilesToMol("CCO");
    if (!mol) {
        std::cerr << "Failed to parse SMILES" << std::endl;
        return 1;
    }
    std::cout << "Molecule: CCO" << std::endl;
    std::cout << "Atoms: " << mol->getNumAtoms() << std::endl;
    std::cout << "Bonds: " << mol->getNumBonds() << std::endl;
    delete mol;
    return 0;
}
