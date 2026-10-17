// Consumer test for libsedml: exercises the real C++ API end to end.
// 1) create a SED-ML L1V4 document in memory (uniform time course +
//    algorithm + KiSAO lookup), 2) serialize it, 3) read it back and
//    validate that the error log is clean. Every check is a genuine API
//    call; the program exits non-zero on the first failure and finally
//    prints an HMBS_TEST_PACKAGE_RESULT evidence marker with real counts.
// NOTE: this test uses only in-memory strings (writeSedMLToStdString /
// readSedMLFromString) and never touches /tmp or any hardcoded temp path,
// so it is robust on hosts where /tmp is read-only (HMBS injects TMPDIR;
// there is simply no temp file to relocate here).
#include <cstdio>
#include <cstring>
#include <string>

#include <sedml/SedDocument.h>
#include <sedml/SedWriter.h>
#include <sedml/SedTypes.h>
#include <sedml/SedUniformTimeCourse.h>
#include <sedml/common/libsedml-version.h>

LIBSEDML_CPP_NAMESPACE_USE

static int g_passed = 0;
static int g_total = 0;

#define CHECK(cond, msg) do { \
    ++g_total; \
    if (cond) { ++g_passed; printf("ok: %s\n", msg); } \
    else { printf("FAIL: %s\n", msg); } \
} while (0)

int main()
{
    printf("libsedml headers version: %s\n", LIBSEDML_DOTTED_VERSION);
    CHECK(strcmp(LIBSEDML_DOTTED_VERSION, "2.0.33") == 0,
          "header version matches 2.0.33");
    CHECK(std::string(getLibSEDMLDottedVersion()) == LIBSEDML_DOTTED_VERSION,
          "linked library version matches headers");

    // Build a document: one uniform time course simulation.
    // SedUniformTimeCourse has four REQUIRED attributes (initialTime,
    // outputStartTime, outputEndTime, numberOfPoints); leaving them unset
    // makes the document schema-invalid so the read-back error log is
    // non-empty (preflight 2026-09-16: 9/10, "round-tripped document has
    // zero errors" failed). Set all four so the round-trip is clean.
    SedDocument doc(1, 4);
    CHECK(doc.getLevel() == 1 && doc.getVersion() == 4,
          "document level 1 version 4");
    SedUniformTimeCourse* sim = doc.createUniformTimeCourse();
    CHECK(sim != NULL, "createUniformTimeCourse returns object");
    if (sim != NULL) {
        sim->setId("sim1");
        sim->setInitialTime(0.0);
        sim->setOutputStartTime(0.0);
        sim->setOutputEndTime(10.0);
        sim->setNumberOfPoints(100);
        SedAlgorithm* alg = sim->createAlgorithm();
        CHECK(alg != NULL, "simulation owns an algorithm slot");
        if (alg != NULL) {
            alg->setKisaoID("KISAO:0000019");
        }
    }

    // KiSAO lookups are compiled into the library: deterministic check.
    SedAlgorithm probe(1, 4);
    probe.setKisaoID(64);
    CHECK(strcmp(probe.getName().c_str(), "Runge-Kutta based method") == 0,
          "KiSAO 64 resolves to Runge-Kutta based method");

    // Serialize and read back.
    SedWriter writer;
    std::string xml = writer.writeSedMLToStdString(&doc);
    CHECK(!xml.empty() && xml.find("sim1") != std::string::npos,
          "serialized document contains sim1");

    SedDocument* back = readSedMLFromString(xml.c_str());
    CHECK(back != NULL, "readSedMLFromString returns document");
    if (back != NULL) {
        unsigned int nErr = back->getNumErrors(LIBSEDML_SEV_ERROR);
        if (nErr != 0) {
            for (unsigned int i = 0; i < back->getNumErrors(); ++i) {
                const SedError* e = back->getError(i);
                if (e != NULL) {
                    printf("sedml error %u: id=%d severity=%d: %s\n",
                           i, e->getErrorId(), e->getSeverity(),
                           e->getMessage().c_str());
                }
            }
        }
        CHECK(nErr == 0,
              "round-tripped document has zero errors");
        CHECK(back->getLevel() == 1 && back->getVersion() == 4,
              "round-tripped level/version preserved");
        delete back;
    }

    bool all_ok = (g_passed == g_total);
    printf("test summary: %d/%d checks passed\n", g_passed, g_total);
    printf("HMBS_TEST_PACKAGE_RESULT={\"executed\":true,\"passed\":%s,"
           "\"command\":\"./test_sedml\",\"discovered\":%d,\"passedCount\":%d}\n",
           all_ok ? "true" : "false", g_total, g_passed);
    return all_ok ? 0 : 1;
}
