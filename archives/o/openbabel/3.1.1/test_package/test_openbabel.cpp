// Consumer end-to-end test for openbabel/3.1.1 on HarmonyOS PC (aarch64).
//
// Exercises the real library pipeline (not a stub):
//   1. OBConversion + OBMol: parse SMILES "CCO" (ethanol), convert to
//      canonical SMILES and molecular formula.
//   2. Round-trip: MOL (V2000) -> SMILES via OBConversion.
//   3. InChI generation via the bundled inchi integration
//      (src/formats/getinchi.cpp compiled into libopenbabel).
//   4. Descriptor API: MW / exact mass via OBDescriptor.
//
// Data files (atomtype.txt etc.) are resolved through BABEL_DATADIR, set by
// test_package/conanfile.py to the packaged share/openbabel directory.

#include <cstdio>
#include <cstring>
#include <string>

#include <openbabel/babelconfig.h>
#include <openbabel/mol.h>
#include <openbabel/obconversion.h>
#include <openbabel/descriptor.h>

static int g_failures = 0;

static void expect(bool cond, const char *what, const std::string &got) {
    if (cond) {
        printf("ok - %s (got \"%s\")\n", what, got.c_str());
    } else {
        printf("not ok - %s (got \"%s\")\n", what, got.c_str());
        g_failures++;
    }
}

int main() {
    // 1. SMILES -> OBMol -> canonical SMILES + formula
    OpenBabel::OBConversion conv;
    expect(conv.SetInAndOutFormats("SMI", "CAN"),
           "SMI/CAN formats registered", conv.GetInFormat()->GetID());

    OpenBabel::OBMol mol;
    bool parsed = conv.ReadString(&mol, "CCO");
    expect(parsed, "SMILES 'CCO' parsed", parsed ? "true" : "false");
    // OpenBabel keeps hydrogens implicit until AddHydrogens(): CCO has
    // 3 heavy atoms / 2 bonds.
    expect(mol.NumAtoms() == 3, "ethanol has 3 heavy atoms",
           std::to_string(mol.NumAtoms()));
    expect(mol.NumBonds() == 2, "ethanol has 2 heavy-atom bonds",
           std::to_string(mol.NumBonds()));

    bool reparsed = conv.ReadString(&mol, "CCO");
    std::string cansmi = reparsed ? conv.WriteString(&mol) : std::string();
    expect(cansmi.find("CCO") != std::string::npos,
           "canonical SMILES contains 'CCO'", cansmi);

    std::string formula = mol.GetFormula();
    expect(formula == "C2H6O", "formula of ethanol is C2H6O", formula);

    // 2. MOL (V2000) -> SMILES round trip
    static const char kEthanolMol[] =
        "ethanol\n  OM  \n\n"
        "  3  2  0  0  0  0  0  0  0  0999 V2000\n"
        "    0.0000    0.0000    0.0000 C   0  0\n"
        "    1.0000    0.0000    0.0000 C   0  0\n"
        "    2.0000    0.0000    0.0000 O   0  0\n"
        "  1  2  1  0\n"
        "  2  3  1  0\n"
        "M  END\n";
    OpenBabel::OBConversion conv2;
    conv2.SetInAndOutFormats("MOL", "SMI");
    OpenBabel::OBMol mol2;
    bool mol_parsed = conv2.ReadString(&mol2, kEthanolMol);
    expect(mol_parsed && mol2.NumAtoms() == 3,
           "MOL block parsed (3 heavy atoms)",
           std::to_string(mol2.NumAtoms()));
    std::string smi_out = conv2.WriteString(&mol2);
    expect(smi_out.find("CCO") != std::string::npos,
           "MOL->SMILES yields CCO", smi_out);

    // 3. InChI generation (bundled inchi linked into libopenbabel)
    OpenBabel::OBConversion conv3;
    if (conv3.SetInAndOutFormats("SMI", "INCHI")) {
        OpenBabel::OBMol mol3;
        bool inchi_parsed = conv3.ReadString(&mol3, "CCO");
        std::string inchi = inchi_parsed ? conv3.WriteString(&mol3)
                                         : std::string();
        expect(inchi.find("InChI=1S/C2H6O") != std::string::npos,
               "InChI of ethanol starts with InChI=1S/C2H6O", inchi);
    } else {
        expect(false, "INCHI format registered", "unavailable");
    }

    // 4. Descriptor API: molecular weight of ethanol ~ 46.07
    OpenBabel::OBMol mol4;
    OpenBabel::OBConversion conv4;
    conv4.SetInAndOutFormats("SMI", "SMI");
    conv4.ReadString(&mol4, "CCO");
    OpenBabel::OBDescriptor* desc =
        OpenBabel::OBDescriptor::FindType("MW");
    expect(desc != nullptr, "MW descriptor registered", "MW");
    if (desc) {
        double mw = desc->Predict(&mol4);
        expect(mw > 45.0 && mw < 47.0, "MW(ethanol) ~ 46.07",
               std::to_string(mw));
    }

    if (g_failures == 0) {
        printf("\nALL TESTS PASSED\n");
        return 0;
    }
    printf("\n%d TEST(S) FAILED\n", g_failures);
    return 1;
}
