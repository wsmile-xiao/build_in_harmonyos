/*
    libvcflib 1.0.12 — Conan test_package consumer.

    Builds against the *installed* package only (public headers from
    include/vcflib + include/wfa2lib, static archives from lib/) and exercises:

      * VCF header/record parsing through vcflib::VariantCallFile / vcflib::Variant
      * allele decomposition (Variant::parsedAlternates) on SNP / insertion / deletion
      * utility functions defined in the library (reverse_complement, toUpper,
        allATGCN, entropy)
      * the vendored WFA2 archive through the library's own facade
        (vcflib::WfaVariant), whose translation unit references the WFA2 C API

    Every check prints one line, so the log is self-describing evidence.

    Note on parsedAlternates(): the returned map is keyed by *every* allele of the
    record (the reference allele included), and an indel's vector carries both the
    reference allele and the pure-indel allele.  The checks below assert on that
    (observed) shape instead of assuming one key per ALT.
*/
#include <cmath>
#include <iostream>
#include <string>
#include <vector>

#include "Variant.h"
#include "LeftAlign.hpp"
#include "vcf-wfa.h"

using namespace std;
using namespace vcflib;

static int checks = 0;
static int failures = 0;

static void check(const string& what, bool ok) {
    ++checks;
    if (!ok) {
        ++failures;
    }
    cout << (ok ? "[ok]   " : "[FAIL] ") << what << endl;
}

// Does `alleles` contain a pure indel with the given ref/alt spelling?
// VariantAllele::is_pure_indel() is non-const, hence the non-const parameter.
static bool has_pure_indel(vector<VariantAllele>& alleles, const string& ref,
                           const string& alt) {
    for (size_t i = 0; i < alleles.size(); ++i) {
        if (alleles[i].ref == ref && alleles[i].alt == alt && alleles[i].is_pure_indel()) {
            return true;
        }
    }
    return false;
}

// Does `alleles` contain a plain substitution ref -> alt?
static bool has_substitution(vector<VariantAllele>& alleles, const string& ref,
                             const string& alt) {
    for (size_t i = 0; i < alleles.size(); ++i) {
        if (alleles[i].ref == ref && alleles[i].alt == alt) {
            return true;
        }
    }
    return false;
}

int main(int argc, char** argv) {
    if (argc < 2) {
        cerr << "usage: test_libvcflib <file.vcf>" << endl;
        return 2;
    }
    // VariantCallFile::open() takes a non-const std::string&.
    string path = argv[1];

    VariantCallFile vcf;
    check("VariantCallFile::open() on " + path, vcf.open(path));
    check("VariantCallFile::is_open()", vcf.is_open());
    check("header declares 1 sample (SAMPLE1)", vcf.sampleNames.size() == 1);

    vector<Variant> records;
    Variant var(vcf);
    while (vcf.getNextVariant(var)) {
        records.push_back(var);
    }
    check("3 VCF records parsed", records.size() == 3);
    if (records.size() != 3) {
        cout << "checks=" << checks << " failures=" << failures << endl;
        return 1;
    }

    // ---- record 1: SNP chr1:100 A>T
    Variant& snp = records[0];
    check("record 1 sequenceName == chr1", snp.sequenceName == "chr1");
    check("record 1 position == 100", snp.position == 100);
    check("record 1 ref == A", snp.ref == "A");
    check("record 1 alt size == 1", snp.alt.size() == 1);
    check("record 1 alt[0] == T", !snp.alt.empty() && snp.alt[0] == "T");
    check("record 1 quality == 50", fabs(snp.quality - 50.0) < 1e-9);
    check("record 1 filter == PASS", snp.filter == "PASS");
    check("record 1 INFO/DP == 14",
          snp.info.count("DP") && !snp.info["DP"].empty() && snp.info["DP"][0] == "14");
    map<string, vector<VariantAllele> > snpAlleles = snp.parsedAlternates();
    check("record 1 parsedAlternates() keys are the ref and the alt allele",
          snpAlleles.size() == 2 && snpAlleles.count("A") == 1 && snpAlleles.count("T") == 1);
    check("record 1 alt entry contains the A -> T substitution",
          snpAlleles.count("T") && has_substitution(snpAlleles["T"], "A", "T"));

    // ---- record 2: insertion chr1:200 G>GA
    Variant& ins = records[1];
    check("record 2 position == 200", ins.position == 200);
    check("record 2 alt[0] == GA", !ins.alt.empty() && ins.alt[0] == "GA");
    map<string, vector<VariantAllele> > insAlleles = ins.parsedAlternates();
    check("record 2 decomposes GA into the ref allele plus a pure insertion of A",
          insAlleles.count("GA") && has_pure_indel(insAlleles["GA"], "", "A"));

    // ---- record 3: deletion chr1:300 AT>A
    Variant& del = records[2];
    check("record 3 ref == AT and alt[0] == A",
          del.ref == "AT" && !del.alt.empty() && del.alt[0] == "A");
    map<string, vector<VariantAllele> > delAlleles = del.parsedAlternates();
    check("record 3 decomposes AT>A into the ref allele plus a pure deletion of T",
          delAlleles.count("A") && has_pure_indel(delAlleles["A"], "T", ""));

    // ---- utility functions defined in the library (src/Variant.cpp, src/LeftAlign.cpp)
    check("reverse_complement(ACGT) == ACGT", reverse_complement("ACGT") == "ACGT");
    check("reverse_complement(AaCcGgTt) == aAcCgGtT (case preserving)",
          reverse_complement("AaCcGgTt") == "aAcCgGtT");
    check("toUpper(acgt) == ACGT", toUpper("acgt") == "ACGT");
    check("allATGCN(ACGT) == true", allATGCN("ACGT"));
    check("allATGCN(ACGTN) == true (N is allowed)", allATGCN("ACGTN"));
    check("allATGCN(ACGTX) == false", !allATGCN("ACGTX"));
    check("entropy(AAAA) == 0", fabs(entropy(string("AAAA"))) < 1e-9);

    // ---- vendored WFA2 archive is installed and links (lib/libwfa2.a): go through the
    // library's own C++ facade, whose translation unit references the WFA2 C API.
    VariantCallFile wfaVcf;
    check("re-open the VCF for the WFA facade", wfaVcf.open(path));
    WfaVariant wfa(wfaVcf);
    check("read the first record into the WFA variant", wfaVcf.getNextVariant(wfa));
    map<string, pair<vector<VariantAllele>, bool> > wfaAlleles = wfa.wfa_parsedAlternates();
    check("WfaVariant::wfa_parsedAlternates() returns the alt allele key",
          wfaAlleles.count("T") == 1);
    check("WfaVariant allele is the A -> T substitution",
          wfaAlleles.count("T") && has_substitution(wfaAlleles["T"].first, "A", "T"));

    cout << "checks=" << checks << " failures=" << failures << endl;
    return failures == 0 ? 0 : 1;
}
