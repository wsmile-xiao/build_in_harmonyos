// test_libobjcryst — consumer test calling real ObjCryst++ APIs.
// Three cases, each prints PASS/FAIL and contributes to the
// HMBS_TEST_PACKAGE_RESULT counters emitted by the runner script.
// (R34: real API calls — Crystal2067, CIF parse, version macros.)
#include <cmath>
#include <iostream>
#include <sstream>
#include <string>

#include <ObjCryst/ObjCryst/Crystal.h>
#include <ObjCryst/ObjCryst/CIF.h>
#include <ObjCryst/version.h>

static int g_passed = 0;
static int g_failed = 0;

#define CHECK(cond, label) do { \
    if (cond) { std::cout << "PASS " << label << std::endl; ++g_passed; } \
    else { std::cout << "FAIL " << label << std::endl; ++g_failed; } \
} while (0)

int main() {
    using namespace ObjCryst;

    // Case 1: build an FCC crystal, verify lattice + space group.
    // UnitCell triclinic ctor takes angles in radians (see UnitCell.h);
    // 90 degrees = pi/2 (upstream testlib.cpp degree literal throws
    // "alpha must be within ]0;pi[").
    {
        const float right = 3.14159265358979323846f / 2.0f;
        Crystal fcc(3.523f, 3.523f, 3.523f, right, right, right, "F m -3 m");
        const float a = fcc.GetLatticePar(0);
        CHECK(std::fabs(a - 3.523f) < 1e-3f, "fcc-lattice-a");
        std::string sg = fcc.GetSpaceGroup().GetName();
        CHECK(!sg.empty(), "fcc-spacegroup-nonempty");
    }

    // Case 2: parse a CIF segment (COD 4316154), build crystal from it.
    {
        const char* cif_text =
            "data_4316154\n"
            "_space_group_IT_number           179\n"
            "_symmetry_cell_setting           hexagonal\n"
            "_symmetry_space_group_name_Hall  'P 65 2 (0 0 1)'\n"
            "_symmetry_space_group_name_H-M   'P 65 2 2'\n"
            "_cell_length_a                   11.6980(17)\n"
            "_cell_length_b                   11.6980(17)\n"
            "_cell_length_c                   48.265(10)\n"
            "_cell_angle_alpha                90\n"
            "_cell_angle_beta                 90\n"
            "_cell_angle_gamma                120\n"
            "loop_\n"
            "_atom_site_label\n"
            "_atom_site_type_symbol\n"
            "_atom_site_fract_x\n"
            "_atom_site_fract_y\n"
            "_atom_site_fract_z\n"
            "Re1 Re 0.38627(5) 0.14503(5) 0.710514(10)\n";
        std::istringstream in(cif_text);
        bool ok = false;
        try {
            CIF cif(in);
            Crystal* c = CreateCrystalFromCIF(cif);
            ok = (c != 0);
            if (ok) {
                const float a = c->GetLatticePar(0);
                CHECK(std::fabs(a - 11.698f) < 1e-2f, "cif-lattice-a");
                delete c;
            } else {
                CHECK(false, "cif-lattice-a");
            }
        } catch (...) {
            CHECK(false, "cif-lattice-a");
        }
        CHECK(ok, "cif-crystal-created");
    }

    // Case 3: compile-time version macros match 2022.1.4.
    {
        CHECK(LIBOBJCRYST_VERSION_MAJOR == 2022, "version-major");
        CHECK(LIBOBJCRYST_VERSION_MINOR == 1, "version-minor");
        CHECK(std::string(LIBOBJCRYST_VERSION_STR) == "2022.1.4", "version-str");
    }

    std::cout << "test_libobjcryst: passed=" << g_passed
              << " failed=" << g_failed << std::endl;
    std::cout << "HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":"
              << (g_failed == 0 ? "true" : "false")
              << ",\"command\":\"./test_libobjcryst\",\"discovered\":7,\"passedCount\":"
              << g_passed << "}" << std::endl;
    return g_failed == 0 ? 0 : 1;
}
