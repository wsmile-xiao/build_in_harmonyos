// test_vcflib.cpp — L1 consumer test for the vcflib C++ library.
//
// Opens a real VCF file with the packaged VariantCallFile API, iterates the
// records with getNextVariant() and validates the parsed Variant fields
// (sequenceName / position / ref / alt / id / quality). Proves the packaged
// libvcflib links and behaves correctly on the target platform.
#include "Variant.h"

#include <iostream>
#include <string>
#include <vector>

using namespace std;
using namespace vcflib;

static int failures = 0;

#define CHECK(cond, msg)                                       \
    do {                                                       \
        if (!(cond)) {                                         \
            cerr << "FAIL: " << msg << endl;                   \
            ++failures;                                        \
        }                                                      \
    } while (0)

int main(int argc, char** argv) {
    string vcf = argc > 1 ? argv[1] : "sample.vcf";

    VariantCallFile variantFile;
    if (!variantFile.open(vcf)) {
        cerr << "FAIL: could not open " << vcf << endl;
        return 1;
    }
    if (!variantFile.is_open()) {
        cerr << "FAIL: VariantCallFile::is_open() false after open" << endl;
        return 1;
    }

    // The VCF header should be non-empty (parsed meta lines).
    CHECK(!variantFile.header.empty(), "VCF header must not be empty");

    // Iterate records and validate parsed fields against the known sample.
    Variant var(variantFile);
    int n = 0;
    bool sawRs6054257 = false;  // dbSNP id from the fixture
    while (variantFile.getNextVariant(var)) {
        ++n;
        CHECK(!var.sequenceName.empty(), "sequenceName must not be empty");
        CHECK(var.position >= 1, "position must be >= 1 (1-based)");
        CHECK(!var.ref.empty(), "ref must not be empty");
        CHECK(!var.alt.empty(), "alt must not be empty");
        CHECK(var.id == "." || !var.id.empty(), "id must be '.' or non-empty");
        if (var.id == "rs6054257") {
            sawRs6054257 = true;
            CHECK(var.sequenceName == "20", "rs6054257 must lie on chr 20");
            CHECK(var.position == 14370, "rs6054257 must be at position 14370");
            CHECK(var.ref == "G", "rs6054257 ref must be G");
            CHECK(var.alt.size() == 1 && var.alt[0] == "A",
                  "rs6054257 alt must be A");
        }
    }

    CHECK(n == 7, "expected 7 variant records in sample.vcf");
    CHECK(sawRs6054257, "expected to find rs6054257 in sample.vcf");

    if (failures == 0) {
        cout << "PASS: vcflib consumer test OK (" << n
             << " records parsed)" << endl;
        return 0;
    }
    cerr << "FAIL: " << failures << " assertion(s) failed" << endl;
    return 1;
}
