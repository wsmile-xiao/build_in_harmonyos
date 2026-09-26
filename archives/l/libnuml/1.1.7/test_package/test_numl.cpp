// Consumer test for libnuml 1.1.7 (HarmonyOS PC adaptation).
// Exercises real library APIs: create a NUMLDocument (L1V1), add ontology
// terms + a result component with composite description/values, serialize
// with NUMLWriter, read back with NUMLReader and verify counts. Each CHECK
// line is deterministic; the conan test() counts "CHECK ...: PASS" lines as
// the single source of truth for HMBS_TEST_PACKAGE_RESULT.
#include <cstdio>
#include <iostream>
#include <string>
#include <numl/NUMLTypes.h>

LIBNUML_CPP_NAMESPACE_USE

static int g_passed = 0;
static int g_total = 0;

static void check(const char* name, bool ok, const std::string& detail = "")
{
    ++g_total;
    if (ok) ++g_passed;
    std::cout << "CHECK " << name << ": " << (ok ? "PASS" : "FAIL");
    if (!detail.empty()) std::cout << " (" << detail << ")";
    std::cout << std::endl;
}

int main()
{
    // 1. Build an in-memory L1V1 document.
    NUMLDocument* doc = new NUMLDocument(1, 1);
    check("create_document", doc != NULL);

    OntologyTerm* t1 = doc->createOntologyTerm();
    t1->setId("term1");
    t1->setTerm("Time");
    t1->setSourceTermId("SBO:0000345");
    t1->setOntologyURI("http://www.ebi.ac.uk/sbo/");
    OntologyTerm* t2 = doc->createOntologyTerm();
    t2->setId("term2");
    t2->setTerm("concentration");
    t2->setSourceTermId("SBO:0000196");
    t2->setOntologyURI("http://www.ebi.ac.uk/sbo/");
    check("ontology_terms", doc->getNumOntologyTerms() == 2);

    ResultComponent* rc = doc->createResultComponent();
    rc->setId("rc1");
    CompositeDescription* cd = rc->createCompositeDescription();
    cd->setName("Time");
    cd->setIndexType("double");
    CompositeDescription* sub = cd->createCompositeDescription();
    sub->setName("Species");
    sub->setIndexType("string");
    AtomicDescription* ad = sub->createAtomicDescription();
    ad->setName("Concentration");
    ad->setValueType("double");
    CompositeValue* cv = rc->createCompositeValue();
    cv->setIndexValue("0");
    CompositeValue* sv = cv->createCompositeValue();
    sv->setIndexValue("s1");
    AtomicValue* av = sv->createAtomicValue();
    av->setValue("1.5");
    check("result_component",
          doc->getNumResultComponents() == 1 &&
          rc->getDimension() != NULL &&
          rc->getDimension()->size() == 1);

    // 2. Round-trip through the writer/reader.
    NUMLWriter writer;
    const std::string fname = "hmbs_test_numl.xml";
    bool written = writer.writeNUML(doc, fname);
    FILE* f = std::fopen(fname.c_str(), "rb");
    long fsize = -1;
    if (f != NULL)
    {
        std::fseek(f, 0, SEEK_END);
        fsize = std::ftell(f);
        std::fclose(f);
    }
    check("write_numl", written && fsize > 0, "size=" + std::to_string(fsize));

    NUMLReader reader;
    NUMLDocument* doc2 = reader.readNUML(fname);
    bool readOk = (doc2 != NULL) && (doc2->getNumErrors() == 0) &&
                  (doc2->getNumOntologyTerms() == 2) &&
                  (doc2->getNumResultComponents() == 1);
    check("read_numl", readOk);
    delete doc2;

    // 3. Level/version identity + clean error log on the built doc.
    check("level_version", doc->getLevel() == 1 && doc->getVersion() == 1);
    check("no_errors", doc->getNumErrors() == 0);

    delete doc;
    std::cout << "TEST_NUML_DONE passed=" << g_passed
              << " total=" << g_total << std::endl;
    return (g_passed == g_total) ? 0 : 1;
}
