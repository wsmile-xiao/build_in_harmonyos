//
// Consumer test for libbpp-popgen 2.4.1 on HarmonyOS PC.
//
// Exercises the *public* Bio++ PopGen API through the installed headers and
// the shipped static archives only: allele identifiers, monolocus genotype
// models (mono/bi/multi-allelic), LocusInfo allele bookkeeping (including its
// exception contracts), AnalyzedLoci aggregation and the DataSet/Group/Individual
// container. Every check is deterministic and needs no input files, no network
// and no device.
//
#include <cstring>
#include <iostream>
#include <string>
#include <vector>

#include <Bpp/Version.h>
#include <Bpp/PopGen/BasicAlleleInfo.h>
#include <Bpp/PopGen/BiAlleleMonolocusGenotype.h>
#include <Bpp/PopGen/MonoAlleleMonolocusGenotype.h>
#include <Bpp/PopGen/MultiAlleleMonolocusGenotype.h>
#include <Bpp/PopGen/LocusInfo.h>
#include <Bpp/PopGen/GeneralExceptions.h>
#include <Bpp/PopGen/DataSet/AnalyzedLoci.h>
#include <Bpp/PopGen/DataSet/DataSet.h>

using namespace bpp;

static int g_checks = 0;
static int g_failures = 0;

static void check(bool ok, const std::string& what)
{
    ++g_checks;
    if (ok) {
        std::cout << "PASS: " << what << std::endl;
    } else {
        ++g_failures;
        std::cout << "FAIL: " << what << std::endl;
    }
}

int main()
{
    std::cout << "Bio++ core version string: " << BPP_VERSION << std::endl;

    // ── Allele identifiers ────────────────────────────────────────────────
    BasicAlleleInfo allele1("A1");
    check(allele1.getId() == "A1", "BasicAlleleInfo stores the identifier given at construction");

    allele1.setId("A2");
    check(allele1.getId() == "A2", "BasicAlleleInfo::setId updates the identifier");

    BasicAlleleInfo allele2("A2");
    BasicAlleleInfo allele3("A3");
    check(allele1 == allele2, "BasicAlleleInfo equality compares identifiers");
    check(allele1 != allele3, "BasicAlleleInfo inequality for different identifiers");

    AlleleInfo* cloned = allele1.clone();
    check(cloned != NULL && cloned->getId() == "A2", "BasicAlleleInfo::clone copies the identifier");
    delete cloned;

    // ── Monolocus genotypes ───────────────────────────────────────────────
    BiAlleleMonolocusGenotype homozygote(1, 1);
    check(homozygote.isHomozygous(), "BiAlleleMonolocusGenotype(1,1) is homozygous");
    check(homozygote.getFirstAlleleIndex() == 1 && homozygote.getSecondAlleleIndex() == 1,
          "BiAlleleMonolocusGenotype exposes both allele indices");
    check(homozygote.getAlleleIndex().size() == 2, "BiAlleleMonolocusGenotype returns two allele indices");

    BiAlleleMonolocusGenotype heterozygote(1, 2);
    check(!heterozygote.isHomozygous(), "BiAlleleMonolocusGenotype(1,2) is heterozygous");

    MonoAlleleMonolocusGenotype monoAllelic(5);
    std::vector<size_t> monoIndices = monoAllelic.getAlleleIndex();
    check(monoIndices.size() == 1 && monoIndices[0] == 5,
          "MonoAlleleMonolocusGenotype(5) returns the single allele index");

    std::vector<size_t> rawIndices;
    rawIndices.push_back(3);
    rawIndices.push_back(4);
    rawIndices.push_back(7);
    MultiAlleleMonolocusGenotype multiAllelic(rawIndices);
    check(!multiAllelic.isHomozygous(), "MultiAlleleMonolocusGenotype with distinct indices is heterozygous");
    check(multiAllelic.getAlleleIndex() == rawIndices, "MultiAlleleMonolocusGenotype preserves the allele index vector");

    std::vector<size_t> repeatedIndices(2, 9);
    MultiAlleleMonolocusGenotype repeatedAllelic(repeatedIndices);
    check(repeatedAllelic.isHomozygous(), "MultiAlleleMonolocusGenotype with identical indices is homozygous");

    // ── LocusInfo ─────────────────────────────────────────────────────────
    LocusInfo locus("LOC1");
    check(locus.getName() == "LOC1", "LocusInfo keeps the locus name");
    check(locus.getPloidy() == LocusInfo::DIPLOID, "LocusInfo defaults to the DIPLOID ploidy constant");

    locus.addAlleleInfo(allele1);
    check(locus.getNumberOfAlleles() == 1, "LocusInfo::addAlleleInfo registers the allele");
    check(locus.getAlleleInfoKey("A2") == 0, "LocusInfo::getAlleleInfoKey returns the insertion key");
    check(locus.getAlleleInfoById("A2").getId() == "A2", "LocusInfo::getAlleleInfoById round-trips");

    bool duplicateRejected = false;
    try {
        locus.addAlleleInfo(allele1);
    } catch (const BadIdentifierException&) {
        duplicateRejected = true;
    }
    check(duplicateRejected, "LocusInfo rejects a duplicate allele identifier with BadIdentifierException");

    bool unknownRejected = false;
    try {
        locus.getAlleleInfoById("NOT_THERE");
    } catch (const AlleleNotFoundException&) {
        unknownRejected = true;
    }
    check(unknownRejected, "LocusInfo throws AlleleNotFoundException for an unknown allele identifier");

    // ── AnalyzedLoci ──────────────────────────────────────────────────────
    AnalyzedLoci analyzed(1);
    check(analyzed.getNumberOfLoci() == 1, "AnalyzedLoci(size_t) reserves the requested number of loci");

    analyzed.setLocusInfo(0, locus);
    check(analyzed.getLocusInfoPosition("LOC1") == 0, "AnalyzedLoci finds the locus by name");
    check(analyzed.getNumberOfAlleles()[0] == 1, "AnalyzedLoci reports the allele count of the locus");
    check(analyzed.getPloidyByLocusPosition(0) == LocusInfo::DIPLOID, "AnalyzedLoci reports the locus ploidy");

    analyzed.addAlleleInfoByLocusPosition(0, allele3);
    check(analyzed.getNumberOfAlleles()[0] == 2, "AnalyzedLoci::addAlleleInfoByLocusPosition extends the locus");

    // ── DataSet / Group / Individual ──────────────────────────────────────
    DataSet dataSet;
    check(dataSet.getNumberOfGroups() == 0, "a fresh DataSet has no groups");

    dataSet.addEmptyGroup(7);
    check(dataSet.getNumberOfGroups() == 1, "DataSet::addEmptyGroup creates a group");

    dataSet.addEmptyIndividualToGroup(0, "IND1");
    check(dataSet.getNumberOfIndividualsInGroup(0) == 1, "DataSet::addEmptyIndividualToGroup adds the individual");
    check(dataSet.getIndividualPositionInGroup(0, "IND1") == 0, "DataSet locates the individual by identifier");

    dataSet.deleteIndividualByIdFromGroup(0, "IND1");
    check(dataSet.getNumberOfIndividualsInGroup(0) == 0, "DataSet::deleteIndividualByIdFromGroup removes it");

    // ── Library fingerprint ───────────────────────────────────────────────
    check(std::strlen(BPP_VERSION) > 0, "the Bio++ version header is usable from the packaged includes");

    std::cout << "----------------------------------------" << std::endl;
    std::cout << "checks: " << g_checks << "  failures: " << g_failures << std::endl;
    if (g_failures == 0) {
        std::cout << "ALL PASS" << std::endl;
    }
    return g_failures == 0 ? 0 : 1;
}
